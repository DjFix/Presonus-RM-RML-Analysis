#include "presonus/panel/FxPresetComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

namespace presonus::panel {
struct FxPresetTestAccess {
  static auto &storage(Presonus::Panel::FxPresetComponent &v) {
    return *v.ownedRecalls;
  }
};
struct PresetCacheAccess {
  static int count(const Presonus::Panel::PresetNameCache &v) {
    return v.observers.count();
  }
};
} // namespace presonus::panel
namespace {
using namespace Presonus::Panel;
struct Parameter : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
void *objectAddress, *baseAddress, *vectorAddress, *arrayAddress;
bool watching, arrayFreed, vectorFreed, baseFreed, objectFreed;
char events[16];
int eventCount;
Parameter *parameter;
PresetNameCache *cache;
int expectedObservers;
void event(char c) { events[eventCount++] = c; }
void freed(void *p, bool array) {
  if (!watching || !p)
    return;
  if (p == arrayAddress) {
    assert(array);
    assert(parameter->observers() == 0);
    arrayFreed = true;
  }
  if (p == vectorAddress) {
    assert(parameter->observers() == 0);
    assert(!arrayAddress || arrayFreed);
    vectorFreed = true;
    event('V');
  }
  if (p == baseAddress) {
    assert(presonus::panel::PresetCacheAccess::count(*cache) == 0);
    baseFreed = true;
  }
  if (p == objectAddress) {
    assert(baseFreed && vectorFreed);
    objectFreed = true;
    event('D');
  }
}
bool childDestroyed;
struct ChildServices : presonus::fx_preset_recall_port::FxRecallServices {
  int infoCalls = 0;
  Core::Portable::FileName presetPath(unsigned, const char *) override {
    std::abort();
  }
  void presetInfo(char *name, int capacity, unsigned slot,
                  const char *) override {
    assert(capacity >= 2 && slot == 0);
    name[0] = '0';
    name[1] = 0;
    ++infoCalls;
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    std::abort();
  }
};
struct Child : FXPresetRecallComponent {
  using FXPresetRecallComponent::FXPresetRecallComponent;
  ~Child() override { childDestroyed = true; }
};
struct Sink : PresetNameCache::ObserverSink {
  void changed(PresetNameCache::Delegate *, PresetNameCache &, int,
               const char *, const char *) override {
    std::abort();
  }
  void rebuilt(PresetNameCache::Delegate *, PresetNameCache &) override {
    std::abort();
  }
};
struct Services : presonus::panel::PresetApplicationServices {
  int selectedSlot(const PresetComponent &) const override { return 0; }
  bool slotEmpty(const PresetComponent &, unsigned) const override {
    return true;
  }
  void slotFileName(Core::CString256 &, const PresetComponent &,
                    unsigned) const override {
    std::abort();
  }
  const char *presetFolder(const PresetComponent &) const override {
    return "fx";
  }
  void ensureNameManager() const override {
    if (watching) {
      assert(vectorFreed);
      assert(parameter->observers() == 0);
      assert(presonus::panel::PresetCacheAccess::count(*cache) ==
             expectedObservers);
      event('B');
    }
  }
  PresetNameCache *lookupCache(const char *folder) const override {
    assert(std::string(folder) == "fx");
    return cache;
  }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    return false;
  }
  void presetInfo(Core::CString64 &, Core::CString32 &, int,
                  const char *) const override {
    std::abort();
  }
  const char *emptyNameMarker() const override { return "empty"; }
  void updateSelection(PresetComponent &) override { std::abort(); }
  int recallAttributes(PresetComponent &, Core::Portable::Attributes &,
                       bool) override {
    std::abort();
  }
  void notifyDelegate(PresetComponent::Delegate *, const PresetComponent &, int,
                      bool) const override {
    std::abort();
  }
};
} // namespace
void operator delete(void *p) noexcept {
  freed(p, false);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept {
  freed(p, false);
  std::free(p);
}
void operator delete[](void *p) noexcept {
  freed(p, true);
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  freed(p, true);
  std::free(p);
}

int main(int argc, char **argv) {
  assert(argc == 5);
  const int variant = std::atoi(argv[1]);
  const bool observe = std::atoi(argv[2]);
  const int count = std::atoi(argv[3]);
  const bool cacheObserve = std::atoi(argv[4]);
  Core::Portable::ParamInfo info{};
  Parameter p(info);
  parameter = &p;
  Sink sink;
  PresetNameCache c("fx", Core::Portable::FileName("unused"), 0, 0, sink);
  cache = &c;
  Services services;
  Core::Portable::NumericParam childParameter(info);
  ChildServices childServices;
  auto child = std::make_unique<Child>(childServices, childParameter,
                                       childParameter, childParameter,
                                       childParameter, childParameter, "fx", 0);
  FXPresetRecallComponent *items[3] = {child.get(), child.get(), child.get()};
  auto *fx =
      new FxPresetComponent(services, observe ? &p : nullptr, items, count);
  auto *base = fx->sourcePortPreset();
  // A borrowed opaque registration token; the actual cache never dereferences
  // it on removal, and no fabricated original Delegate definition is needed.
  int token;
  if (cacheObserve)
    base->sourcePortObserveCache(
        reinterpret_cast<PresetNameCache::Delegate *>(&token));
  expectedObservers = cacheObserve ? 1 : 0;
  assert(p.observers() == (observe ? 1 : 0));
  assert(presonus::panel::PresetCacheAccess::count(c) == expectedObservers);
  auto &storage = presonus::panel::FxPresetTestAccess::storage(*fx);
  assert(storage.count() == count);
  arrayAddress = storage.getItems();
  vectorAddress = &storage;
  baseAddress = base;
  objectAddress = fx;
  assert(fx->getRecallParameter(-1, 4) == nullptr);
  assert(fx->getRecallParameter(0, 4) == nullptr);
  fx->presetStored(*base, 0);
  assert(childServices.infoCalls == count);
  Core::Portable::Component fxProvider;
  fx->fxParameters = &fxProvider;
  assert(fx->getFxIndex() == 0);
  assert(std::string(fx->getPresetType()).empty());
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  assert(!fx->recall(attributes, false));
  watching = true;
  if (variant == 0)
    delete fx; // Actual host virtual deleting destructor and operator delete.
  else {
    fx->~FxPresetComponent(); // Host complete/base variants alias, checked by
                              // nm.
    assert(!objectFreed);
  }
  watching = false;
  assert(vectorFreed && baseFreed && (!arrayAddress || arrayFreed));
  assert(objectFreed == (variant == 0));
  assert(p.observers() == 0);
  assert(!childDestroyed && child->getSlotNum() == 0);
  assert(presonus::panel::PresetCacheAccess::count(c) == 0);
  if (variant != 0)
    ::operator delete(fx);
  // Preserve borrowed mode and its independent, limited lifecycle.
  FxPresetComponent borrowed(nullptr, 0);
  assert(!borrowed.sourcePortPreset());
  assert(!borrowed.getRecallParameter(0, 0));
  assert(!borrowed.recall(attributes, true));
  PresetComponent regressionBase(services);
  borrowed.presetStored(regressionBase, 0);
  FxPresetComponent borrowedChildren(items, 3);
  borrowedChildren.presetStored(regressionBase, 0);
  assert(childServices.infoCalls == count + 3);
  borrowed.presetType = "test";
  borrowed.presetTypeBound = true;
  assert(std::string(borrowed.getPresetType()) == "test");
  std::cout << events << ' ' << (count > 0 && arrayFreed) << '\n';
}
