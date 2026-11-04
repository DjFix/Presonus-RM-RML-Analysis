#include "core/portable/corepersistence.h"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <iomanip>
#include <iostream>
#include <memory>
#include <new>
#include <pthread.h>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
namespace allocations {
struct Entry {
  void *pointer{};
  std::size_t size{};
  bool alive{};
  unsigned frees{};
  std::uintptr_t liveVptr{}, deleteVptr{};
};
static Entry entries[4096];
static std::size_t used = 0;
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static std::atomic<bool> enabled{false};
static void marker() {}
static std::size_t findHandler(std::uintptr_t expected) {
  Dl_info executable{};
  if (!dladdr(reinterpret_cast<void *>(&marker), &executable))
    throw std::runtime_error("executable load base missing");
  pthread_mutex_lock(&mutex);
  for (std::size_t i = 0; i < used; ++i) {
    if (!entries[i].alive || entries[i].size < 2 * sizeof(void *))
      continue;
    void *vptr = nullptr;
    std::memcpy(&vptr, entries[i].pointer, sizeof(vptr));
    Dl_info mapped{};
    if (!dladdr(vptr, &mapped) || mapped.dli_fbase != executable.dli_fbase)
      continue;
    void *functions[2]{};
    std::memcpy(functions, vptr, sizeof(functions));
    const auto offset = reinterpret_cast<std::uintptr_t>(functions[1]) -
                        reinterpret_cast<std::uintptr_t>(executable.dli_fbase);
    if (offset == expected) {
      entries[i].liveVptr = reinterpret_cast<std::uintptr_t>(vptr);
      pthread_mutex_unlock(&mutex);
      return i;
    }
  }
  pthread_mutex_unlock(&mutex);
  throw std::runtime_error("live exact local deleting destructor not found");
}
} // namespace allocations
void *operator new(std::size_t size) {
  void *p = std::malloc(size ? size : 1);
  if (!p)
    throw std::bad_alloc();
  if (allocations::enabled.load()) {
    pthread_mutex_lock(&allocations::mutex);
    if (allocations::used < 4096)
      allocations::entries[allocations::used++] = {p, size, true, 0};
    pthread_mutex_unlock(&allocations::mutex);
  }
  return p;
}
void operator delete(void *p) noexcept {
  if (!p)
    return;
  pthread_mutex_lock(&allocations::mutex);
  std::size_t found = 4096;
  for (std::size_t i = allocations::used; i > 0; --i)
    if (allocations::entries[i - 1].pointer == p &&
        allocations::entries[i - 1].alive) {
      found = i - 1;
      break;
    }
  if (found != 4096 &&
      allocations::entries[found].size >= sizeof(std::uintptr_t))
    std::memcpy(&allocations::entries[found].deleteVptr, p,
                sizeof(std::uintptr_t));
  std::free(p); // actual deallocation, not an appended delete event
  if (found != 4096) {
    allocations::entries[found].alive = false;
    ++allocations::entries[found].frees;
  }
  pthread_mutex_unlock(&allocations::mutex);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
using namespace Core;
using namespace Core::Portable;
using namespace Presonus::Mixer;
namespace {
std::string quote(const std::string &v) {
  std::ostringstream s;
  s << std::quoted(v);
  return s.str();
}
struct ChannelServices : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const ChannelComponent &) const override { return false; }
  void removeLink(ChannelComponent &) override {}
  ChannelComponent *linkablePair(ChannelComponent &) override {
    return nullptr;
  }
  void faderLocateDirty(ChannelComponent &) override {}
  void coefficientsChanged(ChannelComponent &, bool) override {}
};
struct Parameters : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct Observed : StringParam {
  std::vector<std::string> &trace;
  int channel, tag;
  Observed(const ParamInfo &info, std::vector<std::string> &t, int c, int g)
      : StringParam(info), trace(t), channel(c), tag(g) {}
  void toString(char *out, int size) const override {
    trace.push_back("[\"toString\"," + std::to_string(channel) + "," +
                    std::to_string(tag) + "," + std::to_string(size) + "]");
    StringParam::toString(out, size);
  }
  void fromString(CStringPtr text, bool edit) override {
    trace.push_back("[\"fromString\"," + std::to_string(channel) + "," +
                    std::to_string(tag) + "," + quote(text) + "," +
                    (edit ? "1" : "0") + "]");
    StringParam::fromString(text, edit);
  }
};
[[maybe_unused]] void drain() {
  auto &manager = FileIOManager::instance();
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(10);
  do {
    manager.idle();
    if (std::chrono::steady_clock::now() > deadline)
      throw std::runtime_error("file worker timeout");
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  } while (manager.hasTasks());
  manager.idle();
}
} // namespace
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  const int method = std::atoi(argv[1]);
  if (method == 8 && argc == 7) {
    const auto bits =
        static_cast<std::uint32_t>(std::strtoul(argv[2], nullptr, 10));
    float mode;
    std::memcpy(&mode, &bits, sizeof(mode));
    const int count = std::atoi(argv[3]), index = std::atoi(argv[4]),
              missing = std::atoi(argv[5]);
    MixerComponentBase mixer;
    Parameters cascade;
    const ParamInfo cascadeInfo =
        PARAM_FLOAT(5, "cascade", 0, 3, 0, 1, nullptr, nullptr, 0, 0);
    auto *value = new NumericParam(cascadeInfo);
    value->setValue(mode, false);
    cascade.add(value);
    mixer.cascadeParameters = &cascade;
    mixer.hardwareMicLineInputs = static_cast<std::uint32_t>(count);
    mixer.cascadeStatePending = true;
    const ParamInfo info[] = {PARAM_STRING(0, "number", 0),
                              PARAM_STRING(1, "label", 0),
                              PARAM_STRING(2, "name", 0)};
    ChannelServices services;
    std::vector<std::unique_ptr<presonus::mixer::ChannelState>> channelStates;
    std::vector<std::unique_ptr<ChannelComponent>> channels;
    std::vector<std::unique_ptr<Parameters>> owners;
    std::vector<std::string> trace;
    std::vector<std::vector<Observed *>> params;
    for (int i = 0; i < count; ++i) {
      owners.emplace_back(new Parameters);
      std::vector<Observed *> row;
      for (int tag = 0; tag < 3; ++tag) {
        auto *p = new Observed(info[tag], trace, i, tag);
        p->StringParam::fromString(tag == 0   ? "number"
                                   : tag == 1 ? "label"
                                              : argv[6],
                                   false);
        row.push_back(p);
        if (!(missing & (1 << tag)))
          owners.back()->add(p);
      }
      params.push_back(row);
      channelStates.emplace_back(new presonus::mixer::ChannelState);
      channels.emplace_back(
          new ChannelComponent(*channelStates.back(), services));
      mixer.inputChannels.add(channels.back().get());
    }
    mixer.channelIdentity = [&](ChannelComponent *channel) {
      for (int i = 0; i < count; ++i)
        if (channels[i].get() == channel)
          return std::pair<std::int32_t, std::int32_t>{0, index + i};
      throw std::logic_error("unknown test channel");
    };
    mixer.bindInputChannelNaming([&](ChannelComponent *channel) -> Component * {
      for (int i = 0; i < count; ++i)
        if (channels[i].get() == channel)
          return owners[i].get();
      return nullptr;
    });
    assert(mixer.numHWMicLineIn() == static_cast<unsigned>(count));
    assert(mixer.getSpectrumSendSlot() == static_cast<unsigned>(count + 12));
    if (count == 2 && index == 0) {
      assert(mixer.getLinkableChannelPair(channels[0].get()) ==
             channels[1].get());
      assert(mixer.getLinkableChannelPair(channels[1].get()) ==
             channels[0].get());
    }
    mixer.onCascadeStateChange();
    std::cout << "{\"pending\":" << mixer.cascadeStatePending
              << ",\"states\":[";
    for (int i = 0; i < count; ++i) {
      if (i)
        std::cout << ',';
      std::cout << '[';
      for (int tag = 0; tag < 3; ++tag) {
        if (tag)
          std::cout << ',';
        std::cout << quote(params[i][tag]->getText().str());
      }
      std::cout << ']';
    }
    std::cout << "],\"trace\":[";
    for (std::size_t i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << trace[i];
    }
    std::cout << "]}\n";
    for (int i = 0; i < count; ++i)
      for (int tag = 0; tag < 3; ++tag)
        if (missing & (1 << tag))
          delete params[i][tag];
  } else if (method == 7 && argc == 6) {
    const bool present = std::atoi(argv[2]) != 0;
    MixerComponentBase mixer;
    mixer.applicationDataRoot = argv[3];
    mixer.deviceDataFolder = "device";
    const ParamInfo info = PARAM_STRING(4, "accessCode", 0);
    Parameters parameters;
    auto *code = new StringParam(info);
    code->setDefaultText(argv[5]);
    code->fromString(argv[4], false);
    parameters.add(code);
    PermissionsBindings bindings;
    bindings.accessCodeParameters = &parameters;
    bindings.mixer = &mixer;
    PermissionsComponent permissions(bindings);
    mixer.permissions = present ? &permissions : nullptr;
    mixer.resetPermissionsPW();
    FileName path;
    if (present) {
      permissions.getAccessCodeFileName(path);
      const auto deadline =
          std::chrono::steady_clock::now() + std::chrono::seconds(10);
      for (;;) {
        Attributes loaded(AttributeAllocator::getDefault());
        if (ArchiveUtils::loadFromFile(loaded, path.str()))
          break;
        if (std::chrono::steady_clock::now() > deadline)
          throw std::runtime_error("notificationless save timeout");
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
    }
    std::cout << "{\"code\":" << quote(code->getText().str())
              << ",\"path\":" << quote(path.str()) << "}\n";
    FileIOManager::instance().terminate();
  } else if ((method == 9 || method == 10 || method == 11) && argc == 4) {
    const auto expectedD0 =
        static_cast<std::uintptr_t>(std::strtoull(argv[3], nullptr, 10));
    const ParamInfo parameterInfo = PARAM_STRING(9, "gain", PARAM_STORABLE);
    Parameters root;
    auto *child = new Parameters;
    child->setName("channel");
    auto *value = new StringParam(parameterInfo);
    value->fromString("stored", false);
    child->add(value);
    root.addChild(child);
    MixerComponentBase mixer;
    std::vector<std::string> trace;
    std::size_t handlerIndex = 4096;
    mixer.saveServices.parameters = method == 9 ? &root : child;
    mixer.saveServices.inspectCache = [](const FileName &) {
      MixerComponentBase::CacheInfo cache;
      cache.found = true;
      cache.directory = "cache";
      cache.itemCount = 3;
      return cache;
    };
    mixer.saveServices.refreshCache =
        [](const MixerComponentBase::CacheInfo &) {};
    mixer.saveServices.localFile = [](ConstString path) {
      return FileName(path.str());
    };
    mixer.saveServices.saveFlags = [](int, Component *) { return 0; };
    mixer.saveServices.completed = [&](FileName filename, const char *name,
                                       const char *type, int count) {
      handlerIndex = allocations::findHandler(expectedD0);
      trace.push_back("[\"presetSaved\"," + quote(filename.str()) + "," +
                      quote(name) + "," + quote(type) + "," +
                      std::to_string(count) + "]");
    };
    mixer.saveServices.cascadePresetStored = [&](const char *type, int count) {
      trace.push_back("[\"cascadePresetStored\"," + quote(type) + "," +
                      std::to_string(count) + "]");
    };
    if (method == 11) {
      const bool queued = mixer.saveScene(FileName(argv[2]), "ignored", false);
      const auto deadline =
          std::chrono::steady_clock::now() + std::chrono::seconds(10);
      for (;;) {
        Attributes loaded(AttributeAllocator::getDefault());
        if (ArchiveUtils::loadFromFile(loaded, argv[2]))
          break;
        if (std::chrono::steady_clock::now() > deadline)
          throw std::runtime_error("scene no-handler save timeout");
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
      std::cout << "{\"queued\":" << (queued ? "true" : "false") << "}\n";
      FileIOManager::instance().terminate();
      return 0;
    }
    allocations::enabled = true;
    const bool queued =
        method == 9 ? mixer.savePreset(FileName(argv[2]), "Display",
                                       ConstString("channel"))
                    : mixer.saveScene(FileName(argv[2]), "ignored", true);
    drain();
    allocations::enabled = false;
    assert(queued && handlerIndex != 4096);
    const auto entry = allocations::entries[handlerIndex];
    assert(!entry.alive && entry.frees == 1);
    std::cout << "{\"actual_frees\":" << entry.frees
              << ",\"symbol_mapped\":true,\"vptr_rewritten_before_free\":"
              << (entry.liveVptr != entry.deleteVptr ? "true" : "false")
              << ",\"trace\":[";
    for (std::size_t i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << trace[i];
    }
    std::cout << "]}\n";
    FileIOManager::instance().terminate();
  } else if (method == 0) {
    MixerComponentBase missing;
    bool rejected = false;
    try {
      missing.onCascadeStateChange();
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
    missing.hardwareMicLineInputs = 7;
    assert(missing.numHWMicLineIn() == 7 &&
           missing.getSpectrumSendSlot() == 19);
    missing.channelIdentity = [](ChannelComponent *) {
      return std::pair<std::int32_t, std::int32_t>{0, 0};
    };
    rejected = false;
    try {
      missing.bindInputChannelNaming(
          [](ChannelComponent *) -> Component * { return nullptr; });
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
    missing.hardwareMicLineInputs = 0;
    missing.bindInputChannelNaming(
        [](ChannelComponent *) -> Component * { return nullptr; });
    missing.hardwareMicLineInputs = 1;
    rejected = false;
    try {
      (void)missing.numHWMicLineIn();
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
    rejected = false;
    try {
      (void)missing.getLinkableChannelPair(nullptr);
    } catch (const std::logic_error &) {
      rejected = true;
    }
    assert(rejected);
    std::cout << "binding guards and raw getter compatibility PASS\n";
  } else
    return 2;
  return 0;
}
