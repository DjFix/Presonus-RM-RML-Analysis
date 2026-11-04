#include "core/portable/corepersistence.h"
#include "core/portable/coreworker.h"
#include "presonus/panel/FxPresetComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/reconstruction200/large02_w06.hpp"
#include <condition_variable>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <string>
using namespace Core::Portable;
using namespace Presonus::Panel;
struct Observations {
  int children = 0, deallocated = 0, recalled = 0, stored = 0, loaded = 0,
      saved = 0, scheduled = 0;
  std::string mode, name, category;
  int slot = -1;
};
struct Child : Component {
  Observations &o;
  explicit Child(Observations &o) : o(o) {}
  ~Child() override { ++o.children; }
};
struct Parameters : Component {
  Observations &o;
  bool succeeds;
  Parameters(Observations &o, bool succeeds) : o(o), succeeds(succeeds) {}
  void text(int tag, const char *text) {
    auto *info = new ParamInfo PARAM_STRING(tag, "name", 0);
    auto *p = new StringParam(*info, true);
    paramList.add(p);
    p->fromString(text, false);
  }
  void value(int tag, float value) {
    auto *info = new ParamInfo PARAM_FLOAT(tag, "value", -100, 100, 0, 1,
                                           nullptr, 0, 0, 0);
    auto *p = new NumericParam(*info, true);
    paramList.add(p);
    p->setValue(value, false);
  }
  bool load(const InputStorage &s) override {
    ++o.loaded;
    o.mode = s.getMode();
    return succeeds;
  }
  bool save(OutputStorage &s) const override {
    ++o.saved;
    o.mode = s.getMode();
    return true;
  }
};
struct CacheSink : PresetNameCache::ObserverSink {
  Observations &o;
  int changes = 0;
  explicit CacheSink(Observations &o) : o(o) {}
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int slot,
               const char *name, const char *category) override {
    ++changes;
    o.name = name;
    o.category = category;
    o.slot = slot;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {}
};
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameCache *cache = nullptr;
  int slot = 1;
  Observations &o;
  explicit Services(Observations &o) : o(o) {}
  int selectedSlot(const PresetComponent &) const override { return slot; }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    return false;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {}
  const char *presetFolder(const PresetComponent &) const override {
    return "channel";
  }
  void ensureNameManager() const override {}
  PresetNameCache *lookupCache(const char *) const override { return cache; }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    return true;
  }
  void presetInfo(Core::CString64 &n, Core::CString32 &c, int,
                  const char *) const override {
    n = "Preset";
    c = "Cat";
  }
  const char *emptyNameMarker() const override { return "* Empty Location *"; }
  void updateSelection(PresetComponent &) override {}
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    return 1;
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool stored) const override {
    if (stored)
      ++o.stored;
    else
      ++o.recalled;
  }
};
template <class T> struct Setup : T {
  using T::T;
  static Observations *deletionObserver;
  static void operator delete(void *p) noexcept {
    if (deletionObserver)
      ++deletionObserver->deallocated;
    ::operator delete(p);
  }
  void text(int tag, const char *text) {
    auto *i = new ParamInfo PARAM_STRING(tag, "name", 0);
    auto *p = new StringParam(*i, true);
    this->paramList.add(p);
    p->fromString(text, false);
  }
  void value(int tag, float value) {
    auto *i = new ParamInfo PARAM_FLOAT(tag, "value", -100, 100, 0, 1, nullptr,
                                        0, 0, 0);
    auto *p = new NumericParam(*i, true);
    this->paramList.add(p);
    p->setValue(value, false);
  }
};
template <class T> Observations *Setup<T>::deletionObserver = nullptr;
std::string text(Component &c, int tag) {
  Core::CString256 s;
  c.getParameterByTag(tag)->toString(s.getBuffer(), s.getSize());
  return s.str();
}
void check(bool value, const char *message) {
  if (!value)
    throw std::runtime_error(message);
}
// Test-only completion fence. The real FileIOManager owns this FIFO task.
// Its destruction happens after WorkerThread::setCurrentTask(nullptr) has
// released the worker lock. Waiting on notificationQueue alone is too early:
// DataSaveTask marks its entry completed before clearing currentTask.
struct FileIOFenceState {
  std::mutex mutex;
  std::condition_variable changed;
  bool destroyed = false;
};
struct FileIOFence final : BackgroundTask {
  FileIOFenceState &state;
  explicit FileIOFence(FileIOFenceState &state) : state(state) {}
  void work() override {}
  ~FileIOFence() override {
    std::lock_guard<std::mutex> lock(state.mutex);
    state.destroyed = true;
    state.changed.notify_one();
  }
};
void finishFileIO() {
  auto &manager = FileIOManager::instance();
  while (manager.hasTasks()) {
    FileIOFenceState state;
    manager.addExternalTask(new FileIOFence(state));
    {
      std::unique_lock<std::mutex> lock(state.mutex);
      state.changed.wait(lock, [&] { return state.destroyed; });
    }
    // Deliver actual provider completions while all owner state is still alive.
    manager.idle();
  }
  // Invoke unchanged real cleanup only after the worker finished its queued
  // task and released the lock needed by its task transition.
  manager.terminate();
  manager.idle();
}
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int n = std::stoi(argv[1]), v = std::stoi(argv[2]);
  std::filesystem::path folder(argv[3]);
  std::filesystem::create_directories(folder);
  Observations o;
  CacheSink sink(o);
  Services services(o);
  PresetNameCache cache(n == 16 ? "scene" : "channel", FileName(folder.c_str()),
                        10, 0, sink);
  services.cache = &cache;
  int cacheDelegateToken = 0, presetDelegateToken = 0;
  cache.addObserver(
      reinterpret_cast<PresetNameCache::Delegate *>(&cacheDelegateToken));
  if (v == 1)
    cache.cachePreset("Edit", n == 16 ? "" : "Cat", 1);
  if (v == 2)
    cache.cachePreset("Old", n == 16 ? "" : "Cat", 1);
  const auto oldpath = cache.getFileNameForSlot(1, true);
  if (v == 2) {
    std::ofstream old(oldpath.str());
    old << "old";
  }
  o.name.clear();
  o.category.clear();
  o.slot = -1;
  Parameters channel(o, v == 0), fxParameters(o, true);
  const std::string channelName = n == 3 ? (v == 0   ? "Channel"
                                            : v == 1 ? ""
                                                     : std::string(255, 'C'))
                                         : "Channel";
  channel.text(2, channelName.c_str());
  const float number[3] = {n == 7 ? 1.f : -2.75f, 0.f, 3.75f};
  if (!(n == 8 && v == 0))
    fxParameters.value(13, number[v % 3]);
  Presonus::Mixer::MixerComponentBase mixer;
  mixer.selectedChannel = 0;
  Component *channels[] = {&channel};
  const char *categories[] = {"Cat", "NewCat"};
  Parameters categoryGate(o, true);
  categoryGate.value(78, number[v % 3]);
  presonus::panel::ChannelPresetState state{
      mixer, Core::ConstVector<Component *>(channels, 1), nullptr,
      categoryGate.getParameterByTag(78)};
  std::map<std::string, std::string> out;
  auto set = [&](const char *k, auto value) { out[k] = std::to_string(value); };
  Attributes attributes(AttributeAllocator::getDefault());
  auto init = [&](auto &p) {
    p.value(0, 1);
    p.text(1, "Preset");
    p.text(2, "Edit");
    p.text(3, "User");
    if (!(n == 19 && v == 0))
      p.text(100, "Cat");
    p.addDelegate(
        reinterpret_cast<PresetComponent::Delegate *>(&presetDelegateToken));
  };
  if (n == 1 || n == 9 || n == 10 || n == 11 || n == 12 || n == 13) {
    auto lifetime = [&](auto *p, bool deleting) {
      using P = std::remove_pointer_t<decltype(p)>;
      cache.sourcePortRemoveObserver(
          reinterpret_cast<PresetNameCache::Delegate *>(&cacheDelegateToken));
      p->sourcePortObserveCache(
          reinterpret_cast<PresetNameCache::Delegate *>(&presetDelegateToken));
      cache.addObserver(
          reinterpret_cast<PresetNameCache::Delegate *>(&cacheDelegateToken));
      int extraToken = 0;
      cache.addObserver(
          reinterpret_cast<PresetNameCache::Delegate *>(&extraToken));
      p->addDelegate(
          reinterpret_cast<PresetComponent::Delegate *>(&presetDelegateToken));
      p->addChild(new Child(o));
      P::deletionObserver = &o;
      if (deleting)
        delete p;
      else {
        p->~P();
        ::operator delete(p);
      }
      // All observations live outside the destroyed host object. Never read
      // its members or vptr after destruction.
      P::deletionObserver = nullptr;
      set("base_cleanup", o.children);
      set("deleted", o.deallocated);
      sink.changes = 0;
      cache.cachePreset("After", "Life", 2);
      set("cache_observers_remaining", sink.changes);
    };
    if (n == 1 || n == 13)
      lifetime(new Setup<ChannelPresetComponent>(services, state), n == 13);
    if (n == 9 || n == 11)
      lifetime(new Setup<ScenesComponent>(services, mixer), n == 11);
    if (n == 10 || n == 12)
      lifetime(new Setup<GeqPresetComponent>(
                   services,
                   presonus::panel::GeqPresetState{
                       Core::ConstVector<Component *>(nullptr, 0), nullptr}),
               n == 12);
  } else if (n == 2 || n == 3 || n == 7 || n == 15 || n == 19) {
    Setup<ChannelPresetComponent> p(services, state);
    init(p);
    if (n == 2) {
      const std::string user = v == 0   ? "User"
                               : v == 1 ? ""
                                        : std::string(255, 'U');
      p.getParameterByTag(3)->fromString(user.c_str(), false);
      set("result", p.saveUserName());
      out["channel_name"] = text(channel, 2);
    }
    if (n == 3) {
      p.updatePresetName();
      out["user_name"] = text(p, 3);
    }
    if (n == 7) {
      p.getParameterByTag(0)->setValue(number[v % 3], false);
      services.slot = static_cast<int>(number[v % 3]);
      p.paramChanged(p.getParameterByTag(v == 0 ? 0 : 100), 2);
      out["category"] = text(p, 100);
      set("slot", static_cast<int>(p.getParameterByTag(0)->getValue()));
    }
    if (n == 15) {
      set("result", p.recall(attributes, true));
      set("loaded", o.loaded);
      set("recalled", o.recalled);
      out["mode"] = o.mode;
    }
    if (n == 19) {
      set("result", p.store());
      set("saved", o.saved);
      out["mode"] = o.mode;
      Core::CString64 cachedName;
      Core::CString32 cachedCategory;
      cache.getPresetInfo(cachedName, cachedCategory, 1);
      out["name"] = cachedName.str();
      out["category"] = cachedCategory.str();
      set("username_saved", text(channel, 2) == "User");
      finishFileIO();
      check(o.stored == 2, "actual background completion notification missing");
      Attributes saved(AttributeAllocator::getDefault());
      check(
          ArchiveUtils::loadFromFile(saved, cache.getFileNameForSlot(1, true)),
          "actual background archive was not persisted");
    }
  } else if (n == 5) {
    Component *eqs[] = {v == 0 ? &channel : nullptr};
    presonus::panel::GeqPresetState eqstate{
        Core::ConstVector<Component *>(eqs, 1), nullptr};
    Parameters selection(o, true);
    selection.value(77, 0);
    if (v == 1)
      eqstate.selection = selection.getParameterByTag(77);
    Setup<GeqPresetComponent> p(services, eqstate);
    init(p);
    set("result", p.recall(attributes, false));
    set("loaded", o.loaded);
    set("recalled", o.recalled);
    out["mode"] = o.mode;
  } else if (n == 8 || n == 14) {
    FxPresetComponent p(nullptr, 0);
    p.fxParameters = &fxParameters;
    p.presetTypeBound = v != 0;
    p.presetType = v == 1 ? "reverb" : "delay";
    if (n == 8)
      set("result", p.getFxIndex());
    else
      out["type"] = p.getPresetType();
  } else if (n == 16) {
    services.slot = v == 0 ? 0 : 1;
    mixer.saveServices.parameters = &channel;
    mixer.saveServices.inspectCache = [&](const FileName &) {
      ++o.scheduled;
      Presonus::Mixer::MixerComponentBase::CacheInfo info;
      info.found = true;
      info.itemCount = 0;
      return info;
    };
    mixer.saveServices.saveFlags = [](int, Component *) { return 0; };
    mixer.saveServices.completed = [](FileName, const char *, const char *,
                                      int) {};
    mixer.saveServices.cascadePresetStored = [](const char *, int) {};
    Setup<ScenesComponent> p(services, mixer);
    init(p);
    p.getParameterByTag(0)->setValue(static_cast<float>(services.slot), false);
    set("result", p.store());
    set("stored", o.stored);
    set("old_deleted", v == 2 && !std::filesystem::exists(oldpath.str()));
    set("scheduled", o.scheduled);
    if (v) {
      Core::CString64 cachedName;
      Core::CString32 cachedCategory;
      cache.getPresetInfo(cachedName, cachedCategory, 1);
      out["cache_name"] = cachedName.str();
      out["cache_category"] = cachedCategory.str();
      set("cache_slot", p.getSlotNum());
    }
  } else {
    Setup<PresetComponent> p(services);
    init(p);
    if (n == 4) {
      std::unique_ptr<FileIOCompletionHandler> handler(
          p.createStorageHandler());
      handler->onSaveFileCompleted("ignored");
      set("owner_bound", o.stored == 1);
      set("completion_stored", o.stored);
    }
    if (n == 6) {
      p.getParameterByTag(0)->setValue(number[v % 3], false);
      services.slot = static_cast<int>(number[v % 3]);
      set("result", p.getSlotNum());
    }
    if (n == 17) {
      p.doPresetSave("Edit", "Cat", attributes);
      set("stored", o.stored);
      set("old_deleted", v == 2 && !std::filesystem::exists(oldpath.str()));
      set("scheduled", FileIOManager::instance().hasTasks());
      Core::CString64 cachedName;
      Core::CString32 cachedCategory;
      cache.getPresetInfo(cachedName, cachedCategory, 1);
      out["cache_name"] = cachedName.str();
      out["cache_category"] = cachedCategory.str();
      set("cache_slot", p.getSlotNum());
    }
    if (n == 18) {
      p.cacheUpdated(cache, v == 0 ? 9 : 1, "Updated", "NewCat");
      out["name"] = text(p, 1);
      out["category"] = text(p, 100);
      out["edit"] = text(p, 2);
    }
    finishFileIO();
    if (n == 17) {
      check(o.stored == 2, "actual background completion notification missing");
      Attributes saved(AttributeAllocator::getDefault());
      check(
          ArchiveUtils::loadFromFile(saved, cache.getFileNameForSlot(1, true)),
          "actual background archive was not persisted");
    }
  }
  finishFileIO();
  std::cout << "{";
  bool first = true;
  for (const auto &[key, value] : out) {
    if (!first)
      std::cout << ",";
    first = false;
    std::cout << std::quoted(key) << ":" << std::quoted(value);
  }
  std::cout << "}\n";
}
