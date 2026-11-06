#include "core/portable/corepersistence.h"
#include "core/portable/coreworker.h"
#include "presonus/StormMuteGroupComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <thread>
// Test-only allocation fault boundary for the real CCL Vector constructor.
namespace {
bool failArray = false, captureArray = false;
void *watchedArray = nullptr;
int arrayDeletes = 0;
} // namespace
void *operator new[](std::size_t size) {
  if (failArray) {
    failArray = false;
    throw std::bad_alloc();
  }
  void *p = std::malloc(size);
  if (!p)
    throw std::bad_alloc();
  if (captureArray) {
    watchedArray = p;
    captureArray = false;
  }
  return p;
}
void operator delete[](void *p) noexcept {
  if (p == watchedArray) {
    ++arrayDeletes;
    watchedArray = nullptr;
  }
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}
using namespace Core::Portable;
namespace {
void require(bool b) {
  if (!b)
    throw std::runtime_error("safe-list replay mismatch");
}
struct Services : presonus::storm_mute_port::Services {
  void refreshSip() override {}
  void activate(unsigned) override {}
  Component *connectedClient() override { return nullptr; }
  void muteGroupStored(int) override {}
  bool load(presonus::storm_mute_port::Group &) override { return false; }
};
struct ManagerAccess : Presonus::Panel::PresetNameManager {
  static void set(Presonus::Panel::PresetNameManager *p) { theInstance = p; }
  static Presonus::Panel::PresetNameManager *get() { return theInstance; }
};
struct Sink : Presonus::Panel::PresetNameCache::ObserverSink {
  void changed(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &, int, const char *,
               const char *) override {}
  void rebuilt(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &) override {}
};
struct Tree : Component {
  bool result = true, failLoad = false;
  mutable int saves = 0;
  int loads = 0;
  bool save(OutputStorage &s) const override {
    ++saves;
    return result && Component::save(s);
  }
  bool load(const InputStorage &s) override {
    ++loads;
    if (failLoad)
      throw std::runtime_error("fixture load failure");
    return Component::load(s);
  }
};
} // namespace
int main(int argc, char **argv) {
  try {
    const std::string mode = argv[1];
    if (mode == "manager-unwind") {
      alignas(Presonus::Panel::PresetNameManager) unsigned char
          storage[sizeof(Presonus::Panel::PresetNameManager)];
      Presonus::Panel::PresetNameManager foreign;
      auto *target =
          reinterpret_cast<Presonus::Panel::PresetNameManager *>(storage);
      ManagerAccess::set(std::atoi(argv[3]) ? target : &foreign);
      failArray = true;
      bool threw = false;
      try {
        ::new (storage) Presonus::Panel::PresetNameManager;
      } catch (const std::bad_alloc &) {
        threw = true;
      }
      require(threw);
      std::cout << int(ManagerAccess::get() != nullptr) << '\n';
      ManagerAccess::set(nullptr);
      return 0;
    }
    if (mode == "manager-failure") {
      captureArray = true;
      {
        Presonus::Panel::PresetNameManager lifetime;
        require(watchedArray != nullptr);
      }
      require(arrayDeletes == 1 && watchedArray == nullptr);
      bool threw = false;
      failArray = true;
      try {
        Presonus::Panel::PresetNameManager failed;
      } catch (const std::bad_alloc &) {
        threw = true;
      }
      require(threw);
      auto &retry = Presonus::Panel::PresetNameManager::instance();
      require(retry.sourcePortCacheCount() == 0 &&
              retry.sourcePortCacheCapacity() == 10);
      // Repeated access must keep the same registered instance.
      require(&retry == &Presonus::Panel::PresetNameManager::instance());
      std::cout << "manager allocation unwind and singleton retry passed\n";
      return 0;
    }
    Services services;
    presonus::storm_mute_port::State state(services);
    Presonus::StormMuteGroupComponent storm(state);
    storm.setName("muteGroup");
    Presonus::Panel::PresetNameManager manager;
    state.presetNames = &manager;
    Sink sink;
    Presonus::Panel::PresetNameCache cache(
        "muteGroup",
        FileName("temp/recovery-work/rolling200-02/storm-safe122/files"), 8, 0,
        sink);
    if (mode == "manager") {
      require(manager.sourcePortCacheCapacity() == 10);
      require(manager.sourcePortCacheCount() == 0);
      std::cout << "10 0 5\n";
      return 0;
    }
    if (mode == "filename") {
      if (std::atoi(argv[2]) > 0)
        manager.sourcePortAddCache(&cache);
      if (std::atoi(argv[2]) < 0)
        state.presetNames = nullptr;
      std::cout << storm.getFileName(std::stoul(argv[3])).str() << '\n';
      return 0;
    }
    manager.sourcePortAddCache(&cache);
    const auto path = storm.getSafeListFileName();
    if (mode == "safe") {
      Presonus::Panel::PresetNameManager empty;
      state.presetNames = &empty;
      presonus::storm_mute_port::State otherState(services);
      otherState.presetNames = &empty;
      Presonus::StormMuteGroupComponent other(otherState);
      require(other.getSafeListFileName() == path);
      std::cout << path.str() << '\n';
      return 0;
    }
    // Borrow the very tree used by MixerComponentBase's save implementation.
    Presonus::Mixer::MixerComponentBase mixer;
    Tree tree;
    state.mixer = &mixer;
    mixer.saveServices.parameters = &tree;
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.maxValue = 1.f;
    info.minValue = -1.f;
    info.flags = ParamInfo::kStorable;
    std::strcpy(info.name, "mute");
    tree.addParameters(&info, 1);
    auto *first = tree.getParameterByTag(0);
    auto *child = new Component("child");
    child->addParameters(&info, 1);
    tree.addChild(child);
    auto *second = child->getParameterByTag(0);
    state.mixerMutes.add(first);
    state.mixerMutes.add(second);
    state.mixerMutes.add(first);
    state.loose.add(first);
    state.loose.add(second);
    state.loose.add(first);
    first->setValue(1.f);
    second->setValue(1.f);
    auto wait = [] {
      auto &io = FileIOManager::instance();
      struct Barrier : BackgroundTask {
        void work() override {}
      };
      struct Done : FileIOCompletionHandler {
        bool &done;
        explicit Done(bool &d) : done(d) {}
        void onSaveFileCompleted(const char *) override { done = true; }
      };
      bool done = false;
      io.addExternalTask(new Barrier, "", new Done(done));
      const auto end =
          std::chrono::steady_clock::now() + std::chrono::seconds(5);
      while (!done && std::chrono::steady_clock::now() < end) {
        io.idle();
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
      }
      io.idle();
      require(done && !io.hasTasks());
    };
    FileUtils::deleteFile(path.str());
    if (mode == "store" || mode == "all") {
      tree.result = std::atoi(argv[mode == "store" ? 2 : 4]);
      if (mode == "store")
        storm.storeSafeList();
      else {
        state.enabled = std::atoi(argv[2]);
        storm.onAllMutesChange(std::atoi(argv[3]));
      }
      wait();
      Attributes out(AttributeAllocator::getDefault());
      const bool exists = ArchiveUtils::loadFromFile(out, path.str());
      const bool expected = tree.saves && tree.result;
      require(exists == expected);
      if (exists) {
        require(out.lookup("mute") != nullptr);
        require(out.getAttributes("child") != nullptr);
      }
      std::cout << tree.saves << ' ' << int(exists) << '\n';
      return 0;
    }
    if (mode == "startup" || mode == "exception") {
      const auto bits = mode == "exception"
                            ? 1065353216u
                            : static_cast<unsigned>(std::stoul(argv[2]));
      float value;
      std::memcpy(&value, &bits, 4);
      ParamInfo allInfo = info;
      std::strcpy(allInfo.name, "all");
      storm.addParameters(&allInfo, 1);
      // Real CCL NumericParam supplies the actual tag-zero value.
      storm.getParameterByTag(0)->setValue(value);
      const bool load = mode == "exception" || std::atoi(argv[3]);
      if (load) {
        storm.storeSafeList();
        wait();
      }
      state.enabled = false;
      struct Observer : ParamObserverBase {
        presonus::storm_mute_port::State &state;
        Parameter *first;
        std::string trace;
        Observer(presonus::storm_mute_port::State &s, Parameter *p)
            : state(s), first(p) {}
        void paramChanged(Parameter *p, int msg) override {
          if (msg == Parameter::kChanged) {
            if (!trace.empty())
              trace += ",";
            trace += p == first ? "0:" : "1:";
            trace += state.enabled ? "1" : "0";
          }
        }
      } observer(state, first);
      first->addObserver(&observer);
      second->addObserver(&observer);
      state.delayed.add(second);
      if (mode == "exception") {
        tree.failLoad = true;
        bool threw = false;
        try {
          storm.startup();
        } catch (const std::runtime_error &) {
          threw = true;
        }
        require(threw && !state.enabled && state.loose.isEmpty() &&
                state.delayed.count() == 1);
        tree.failLoad = false;
        storm.startup();
        require(state.enabled && state.loose.count() == 2);
        first->removeObserver(&observer);
        second->removeObserver(&observer);
        std::cout << "load exception preserves disabled state; retry passed\n";
        return 0;
      }
      storm.startup();
      require(state.delayed.count() == 1);
      first->removeObserver(&observer);
      second->removeObserver(&observer);
      require(first->getValue() == 1.f && second->getValue() == 1.f);
      std::cout << int(state.enabled) << ' ' << state.loose.count() << ' '
                << observer.trace << ' ' << tree.loads << '\n';
      FileUtils::deleteFile(path.str());
      return 0;
    }
    std::cerr << "unhandled fixture\n";
    return 2;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
