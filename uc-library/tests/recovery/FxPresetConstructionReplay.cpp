#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/FxPresetComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>

namespace presonus::panel {
struct PresetTestAccess {
  static auto &delegates(Presonus::Panel::PresetComponent &p) {
    return p.delegates;
  }
  static auto &services(Presonus::Panel::PresetComponent &p) {
    return p.services;
  }
  static auto &display(Presonus::Panel::PresetComponent &p) {
    return p.displayName;
  }
};
struct FxPresetTestAccess {
  static auto &recalls(Presonus::Panel::FxPresetComponent &p) {
    return *p.ownedRecalls;
  }
  static void children(Presonus::Panel::FxPresetComponent &p,
                       Presonus::Panel::FXPresetRecallComponent &child) {
    for (int i = 0; i < 3; ++i)
      assert(p.ownedRecalls->add(&child));
    p.recalls = Core::ConstVector<Presonus::Panel::FXPresetRecallComponent *>(
        p.ownedRecalls->getItems(), p.ownedRecalls->count());
  }
  static auto *current(Presonus::Panel::FxPresetComponent &p) {
    return p.currentChild;
  }
  static auto *token(Presonus::Panel::FxPresetComponent &p) {
    return reinterpret_cast<Presonus::Panel::PresetComponent::Delegate *>(
        &p.delegateToken);
  }
};
} // namespace presonus::panel
namespace {
using namespace Presonus::Panel;
using presonus::panel::FxPresetTestAccess;
using presonus::panel::PresetTestAccess;
// Test-only allocator failure/ownership accounting. Fixed storage never
// allocates.
bool tracking = false;
int failAt = -1, attempts = 0, live = 0;
Core::Portable::Parameter *watchedSelection = nullptr;
bool sawObserverBeforeDelegate = false;
void *pointers[4096]{};
void added(void *p) {
  if (!tracking)
    return;
  for (auto &slot : pointers)
    if (!slot) {
      slot = p;
      ++live;
      return;
    }
  std::abort();
}
void removed(void *p) {
  if (!p)
    return;
  for (auto &slot : pointers)
    if (slot == p) {
      slot = nullptr;
      --live;
      return;
    }
}
void *allocate(std::size_t n) {
  if (watchedSelection && watchedSelection->observerList.count()) {
    auto *observer = watchedSelection->observerList[0];
    auto *base = static_cast<PresetComponent *>(observer);
    if (PresetTestAccess::delegates(*base).count() == 0)
      sawObserverBeforeDelegate = true;
  }
  if (tracking && attempts++ == failAt)
    throw std::bad_alloc();
  void *p = std::malloc(n ? n : 1);
  if (!p)
    throw std::bad_alloc();
  added(p);
  return p;
}
struct Services : presonus::panel::PresetApplicationServices {
  mutable int cleanup = 0;
  mutable int externalStored = 0, externalRecalled = 0;
  PresetComponent::Delegate *externalIdentity = nullptr;
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
  void ensureNameManager() const override { ++cleanup; }
  PresetNameCache *lookupCache(const char *) const override { return nullptr; }
  bool hasSelectedSlotParameter(const PresetComponent &) const override {
    return true;
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
  void notifyDelegate(PresetComponent::Delegate *identity,
                      const PresetComponent &, int slot,
                      bool stored) const override {
    assert(identity == externalIdentity && slot == 0);
    if (stored)
      ++externalStored;
    else
      ++externalRecalled;
  }
};
struct ChildServices : presonus::fx_preset_recall_port::FxRecallServices {
  int infoCalls = 0;
  Core::Portable::FileName presetPath(unsigned, const char *) override {
    std::abort();
  }
  void presetInfo(char *name, int capacity, unsigned slot,
                  const char *category) override {
    assert(capacity == 64 && slot == 0 && std::strcmp(category, "fx") == 0);
    std::strcpy(name, "actual notified FX name");
    ++infoCalls;
  }
  presonus::fx_preset_recall_port::FxRecallCache *
  lookupCache(const char *) override {
    std::abort();
  }
};
struct Dependencies : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
struct Formatter : Core::Formatter {
  Formatter() : Core::Formatter("reverbnum") {}
  void print(Data &d) const override { d.string[0] = 0; }
};
void verify(PresetComponent &p, Services &services, const char *name,
            const char *display) {
  assert(&PresetTestAccess::services(p) == &services);
  assert(std::strcmp(p.getName(), name) == 0);
  assert(std::strcmp(PresetTestAccess::display(p), display) == 0);
  assert(p.countParameters() == 4);
  assert(p.getParameterByTag(0)->getFormatter() ==
         Core::FormatterRegistry::find("reverbnum"));
  auto *s = Core::Portable::StringParam::cast(p.getParameterByTag(2));
  assert(s);
  assert(std::strcmp(s->getDefaultText(), display) == 0);
  assert(std::strcmp(s->getText(), display) == 0);
  // Actual provider reset, including a changed string, preserves the default.
  s->fromString("changed", false);
  s->resetValue(false);
  assert(std::strcmp(s->getText(), display) == 0);
  auto &v = PresetTestAccess::delegates(p);
  assert(v.getDelta() == 5);
}
void print(PresetComponent &p, const char *display, int observed) {
  std::cout
      << p.getName() << '|' << display << '|'
      << p.getParameterByTag(0)->getFormatter()->getName() << '|'
      << Core::Portable::StringParam::cast(p.getParameterByTag(2))->getText()
      << '|' << observed << '\n';
  for (int i = 0; i < 4; ++i) {
    auto *v = p.getParameterByTag(i);
    auto &info = *v->info;
    std::cout << info.type << '|' << info.tag << '|' << info.name << '|'
              << info.minValue << '|' << info.maxValue << '|' << info.midValue
              << '|' << info.defaultValue << '|' << info.deltaValue << '|'
              << info.flags << '|' << info.title << '|'
              << (info.unitName ? info.unitName : "") << '|'
              << (info.curveName ? info.curveName : "") << '\n';
  }
}
} // namespace
void *operator new(std::size_t n) { return allocate(n); }
void *operator new[](std::size_t n) { return allocate(n); }
void operator delete(void *p) noexcept {
  removed(p);
  std::free(p);
}
void operator delete[](void *p) noexcept {
  removed(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept {
  removed(p);
  std::free(p);
}
void operator delete[](void *p, std::size_t) noexcept {
  removed(p);
  std::free(p);
}
int main(int argc, char **argv) {
  assert(argc == 3);
  std::string kind = argv[1];
  bool present = std::atoi(argv[2]);
  static Formatter formatter;
  Core::FormatterRegistry::add(&formatter);
  Services services;
  Presonus::Mixer::MixerComponentBase mixer;
  Core::Portable::Component settings;
  presonus::frontpanel_port::State state(settings);
  Dependencies deps;
  FrontPanelComponent front(state, deps);
  static const Core::Portable::ParamInfo info =
      PARAM_INT_(13, "selfx", 0, 3, 0, "", "", 0, 0, "Selected FX", nullptr);
  if (present)
    front.portableState().component.addParameters(&info, 1);
  auto *selection = front.portableState().component.getParameterByTag(13);
  auto observers = [&]() {
    return selection ? selection->observerList.count() : 0;
  };
  // No service binding must throw before observer registration.
  try {
    FxPresetComponent x(front, mixer);
    std::abort();
  } catch (const std::logic_error &) {
  }
  assert(observers() == 0);
  mixer.presetApplicationServices = &services;
  if (kind == "base") {
    PresetComponent p("base", "Display", "reverbnum", mixer);
    verify(p, services, "base", "Display");
    assert(PresetTestAccess::delegates(p).count() == 0);
    print(p, "Display", 0);
    return 0;
  }
  watchedSelection = selection;
  auto *p = new FxPresetComponent(front, mixer);
  auto *base = p->sourcePortPreset();
  verify(*base, services, "fx", "My Fx");
  assert(p->fxParameters == &front.portableState().component);
  assert(observers() == int(present));
  assert(!present || sawObserverBeforeDelegate);
  auto &d = PresetTestAccess::delegates(*base);
  assert(d.count() == 1 && d[0] == FxPresetTestAccess::token(*p));
  auto &r = FxPresetTestAccess::recalls(*p);
  assert(!r.count() && !r.getItems() && r.getDelta() == 5 &&
         !FxPresetTestAccess::current(*p));
  print(*base, "My Fx", observers());
  Core::Portable::NumericParam childSlot(info);
  static const Core::Portable::ParamInfo childNameInfo =
      PARAM_STRING(1, "child_name", 0);
  static const Core::Portable::ParamInfo childTypeInfo =
      PARAM_STRING(2, "child_type", 0);
  Core::Portable::StringParam childName(childNameInfo),
      childType(childTypeInfo);
  ChildServices childServices;
  FXPresetRecallComponent child(childServices, childSlot, childSlot, childType,
                                childName, childSlot, "fx", 0);
  FxPresetTestAccess::children(*p, child);
  int externalToken;
  services.externalIdentity =
      reinterpret_cast<PresetComponent::Delegate *>(&externalToken);
  base->addDelegate(services.externalIdentity);
  base->presetStored(); // Actual base dispatch must reach actual composed Fx.
  assert(childServices.infoCalls == 3 && services.externalStored == 1);
  assert(std::strcmp(childName.getText(), "actual notified FX name") == 0);
  assert(std::strcmp(childType.getText(), "AMBIENCE") == 0);
  // Actual recalled callback must be callable, with native no-side-effect
  // behavior, rather than being forwarded as an unresolved identity token.
  for (int slot : {-2147483647 - 1, -1, 0, 2147483647})
    p->presetRecalled(*base, slot);
  base->presetRecalled();
  assert(childServices.infoCalls == 3 && services.externalRecalled == 1);
  assert(std::strcmp(childName.getText(), "actual notified FX name") == 0);
  assert(std::strcmp(childType.getText(), "AMBIENCE") == 0);
  base->removeDelegate(FxPresetTestAccess::token(*p));
  base->presetStored();
  assert(childServices.infoCalls == 3 && services.externalStored == 2);
  std::cerr << "actual stored notification: 3 child updates, external "
               "delegates preserved, removed membership silent\n";
  delete p;
  assert(!observers());
  // Sweep each real throwing allocation point. Every failed construction must
  // unwind actual Core parameters/vectors and detach any exposed observer.
  int failures = 0;
  bool success = false;
  for (int point = 0; point < 128; ++point) {
    assert(live == 0);
    if (selection)
      selection->observerList.resize(0);
    failAt = point;
    attempts = 0;
    tracking = true;
    try {
      auto *x = new FxPresetComponent(front, mixer);
      delete x;
      success = true;
    } catch (const std::bad_alloc &) {
      ++failures;
    }
    assert(observers() == 0);
    // Parameter outlives Fx; CCL removeObserver retains its reusable capacity.
    // Release that external provider capacity before allocation accounting.
    if (selection)
      selection->observerList.resize(0);
    tracking = false;
    if (live)
      std::cerr << "point=" << point << " live=" << live
                << " attempts=" << attempts << "\n";
    assert(live == 0);
    if (success)
      break;
  }
  watchedSelection = nullptr;
  assert(success && failures > 4);
  std::cerr << "allocation rollback points=" << failures
            << "; actual delete and zero outstanding allocations\n";
}
