#include "presonus/frontier01/frontier01_w01.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include <cassert>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using namespace Presonus::Panel;
using namespace Core::Portable;
namespace presonus::panel {
struct PresetCacheAccess {
  static bool dirty(PresetNameCache &c) { return c.dirty; }
  static void clean(PresetNameCache &c) { c.dirty = false; }
};
} // namespace presonus::panel
namespace {
bool observing = false;
std::vector<std::string> trace;
std::vector<PresetNameCache *> caches;
std::vector<FXPresetRecallComponent *> effects;
void log(const std::string &s) {
  if (observing)
    trace.push_back(s);
}
template <class T> int identity(const std::vector<T *> &v, T *p) {
  for (unsigned i = 0; i < v.size(); ++i)
    if (v[i] == p)
      return int(i);
  throw 10;
}
} // namespace
extern "C" PresetNameCache *realCache(const PresetComponent *) asm(
    "__real__ZNK8Presonus5Panel15PresetComponent8getCacheEv");
extern "C" PresetNameCache *wrapCache(const PresetComponent *p) asm(
    "__wrap__ZNK8Presonus5Panel15PresetComponent8getCacheEv");
extern "C" PresetNameCache *wrapCache(const PresetComponent *p) {
  log("lookup");
  return realCache(p);
}
extern "C" FileName realFile(PresetNameCache *, unsigned, bool) asm(
    "__real__ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb");
extern "C" FileName wrapFile(PresetNameCache *, unsigned, bool) asm(
    "__wrap__ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb");
extern "C" FileName wrapFile(PresetNameCache *p, unsigned s, bool f) {
  log("file:" + std::to_string(s) + ":" + std::to_string(f));
  return realFile(p, s, f);
}
extern "C" void realRebuild(PresetNameCache *) asm(
    "__real__ZN8Presonus5Panel15PresetNameCache7rebuildEv");
extern "C" void wrapRebuild(PresetNameCache *) asm(
    "__wrap__ZN8Presonus5Panel15PresetNameCache7rebuildEv");
extern "C" void wrapRebuild(PresetNameCache *p) {
  if (observing)
    log("rebuild:" + std::to_string(identity(caches, p)) + ":" +
        std::to_string(presonus::panel::PresetCacheAccess::dirty(*p)));
  realRebuild(p);
}
extern "C" void realFx(FXPresetRecallComponent *) asm(
    "__real__ZN8Presonus5Panel23FXPresetRecallComponent12updateFxNameEv");
extern "C" void wrapFx(FXPresetRecallComponent *) asm(
    "__wrap__ZN8Presonus5Panel23FXPresetRecallComponent12updateFxNameEv");
extern "C" void wrapFx(FXPresetRecallComponent *p) {
  if (observing)
    log("fx:" + std::to_string(identity(effects, p)));
  realFx(p);
}
extern "C" void
realControl(void *) asm("__real__ZN8Presonus5Panel7ControlD2Ev");
extern "C" void
wrapControl(void *) asm("__wrap__ZN8Presonus5Panel7ControlD2Ev");
extern "C" void wrapControl(void *p) {
  log("base");
  realControl(p);
}
extern "C" void
realHandler(void *) asm("__real__ZN8Presonus2UC18FileRequestHandlerD2Ev");
extern "C" void
wrapHandler(void *) asm("__wrap__ZN8Presonus2UC18FileRequestHandlerD2Ev");
extern "C" void wrapHandler(void *p) {
  log("base");
  realHandler(p);
}
extern "C" void sceneD1(void *) asm("_ZN16MixerSceneLoaderD1Ev");
extern "C" void spiD1(void *) asm("_ZN8Presonus5Panel10SPIControlD1Ev");
struct Sink : PresetNameCache::ObserverSink {
  int rebuiltCount = 0, changedCount = 0;
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    ++changedCount;
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &c) override {
    assert(!presonus::panel::PresetCacheAccess::dirty(c));
    ++rebuiltCount;
  }
};
struct Services : presonus::panel::PresetApplicationServices {
  PresetNameCache *cache = nullptr;
  mutable int ensures = 0, lookups = 0;
  int selectedSlot(const PresetComponent &) const override { return 0; }
  bool slotEmpty(const PresetComponent &, unsigned) const override { throw 1; }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    throw 1;
  }
  const char *presetFolder(const PresetComponent &) const override {
    return "fixture";
  }
  void ensureNameManager() const override { ++ensures; }
  PresetNameCache *lookupCache(const char *s) const override {
    assert(std::string(s) == "fixture");
    ++lookups;
    return cache;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    throw 1;
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    throw 1;
  }
  const char *emptyNameMarker() const override { return "* Empty Location *"; }
  void updateSelection(PresetComponent &) override { throw 1; }
  int recallAttributes(PresetComponent &, Attributes &, bool) override {
    throw 1;
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    throw 1;
  }
};
struct FxServices : presonus::trial08::FxRecallServices {
  int infoCalls = 0;
  FileName presetPath(unsigned, const char *) override { throw 1; }
  void presetInfo(char *s, int cap, unsigned n, const char *) override {
    ++infoCalls;
    std::snprintf(s, cap, "fixture-%u", n);
  }
  presonus::trial08::FxRecallCache *lookupCache(const char *) override {
    throw 1;
  }
};
struct Stream : Core::IO::Stream {
  int &destroyed;
  explicit Stream(int &v) : destroyed(v) {}
  ~Stream() override { ++destroyed; }
  Core::int64 getPosition() override { return 0; }
  Core::int64 setPosition(Core::int64, int) override { return 0; }
  int readBytes(void *, int) override { throw 1; }
  int writeBytes(const void *, int) override { throw 1; }
};
const ParamInfo numericInfo =
    PARAM_FLOAT(0, "n", -1000, 1000, 0, 1, nullptr, nullptr, 0, 0);
const ParamInfo stringInfo = PARAM_STRING(0, "s", 0);
struct Number : NumericParam {
  Number() : NumericParam(numericInfo) {}
  int observers() const { return observerList.count(); }
};
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const int n = std::stoi(argv[1]);
  const unsigned arg = std::stoul(argv[2]);
  Sink sink;
  FileName folder(argv[3]);
  PresetNameCache cache("preset", folder, 16, 0, sink);
  Services services;
  services.cache = &cache;
  PresetComponent preset(services);
  if (n == 1) {
    assert(arg < 16);
    presonus::panel::PresetCacheAccess::clean(cache);
    cache.cachePreset("  Native Port  ", " Vocal ", arg);
    auto expected = cache.getFileNameForSlot(arg, true);
    observing = true;
    auto result = preset.getFileNameForSlot(arg);
    observing = false;
    assert(std::string(result) == std::string(expected));
    assert(services.ensures == 1 && services.lookups == 1);
    assert(std::string(result).find("Native Port.Vocal.preset") !=
           std::string::npos);
  } else if (n == 2) {
    int destroyed = 0;
    auto *p = new MixerSceneLoader(arg ? new Stream(destroyed) : nullptr);
    observing = true;
    sceneD1(p);
    observing = false;
    assert(destroyed == int(arg));
    ::operator delete(p);
  } else if (n == 3) {
    Number a, b, c;
    Control survivor(9);
    auto *p = new SPIControl(4);
    if (arg) {
      p->setParameter(&a, 0);
      p->setAltParameter(&b);
      p->setTertiaryParameter(&c);
      assert(a.observers() == 1 && b.observers() == 1 && c.observers() == 1);
      auto &v = presonus::panel::ControlAccess::timers();
      v.add(new Control::Timer(p, 1, 0));
      v.add(new Control::Timer(&survivor, 2, 0));
      v.add(new Control::Timer(p, 3, 0));
    }
    observing = true;
    spiD1(p);
    observing = false;
    assert(!a.observers() && !b.observers() && !c.observers());
    auto &v = presonus::panel::ControlAccess::timers();
    assert(v.count() == int(arg));
    if (arg) {
      assert(v[0]->control == &survivor);
      delete v[0];
      v.removeAll();
    }
    ::operator delete(p);
  } else if (n == 4) {
    PresetNameCache b("preset", folder, 16, 0, sink),
        c("preset", folder, 16, 0, sink);
    caches = {&cache, &b, &c};
    PresetNameCache *items[] = {&cache, &b, &c, &cache};
    for (auto *p : caches) {
      presonus::panel::PresetCacheAccess::clean(*p);
      p->addObserver(reinterpret_cast<PresetNameCache::Delegate *>(1));
    }
    PresetNameManager manager(items, arg);
    observing = true;
    manager.rebuildAllCaches();
    observing = false;
    assert(sink.rebuiltCount == int(arg));
    assert(sink.changedCount == int(arg > 3 ? 3 : arg));
    for (auto *p : caches)
      assert(!presonus::panel::PresetCacheAccess::dirty(*p));
  } else if (n == 5) {
    FxServices fx;
    Number slot, loaded, type;
    StringParam label(stringInfo), name(stringInfo);
    slot.setValue(2);
    loaded.setValue(2);
    type.setValue(0);
    FXPresetRecallComponent a(fx, slot, loaded, label, name, type, "fx", 0),
        b(fx, slot, loaded, label, name, type, "fx", 1),
        c(fx, slot, loaded, label, name, type, "fx", 2);
    effects = {&a, &b, &c};
    FXPresetRecallComponent *items[] = {&a, &b, &c, &a};
    FxPresetComponent component(items, arg);
    observing = true;
    component.presetStored(preset, -123);
    observing = false;
    assert(fx.infoCalls == int(arg));
    if (arg) {
      char text[128];
      name.toString(text, 128);
      assert(std::string(text) == "fixture-2");
      label.toString(text, 128);
      assert(std::string(text) == (arg == 3 ? "MONO DELAY" : "AMBIENCE"));
    }
  } else
    return 3;
  for (const auto &s : trace)
    std::cout << s << '\n';
  std::cout << "PROVIDER_OK\n";
}
