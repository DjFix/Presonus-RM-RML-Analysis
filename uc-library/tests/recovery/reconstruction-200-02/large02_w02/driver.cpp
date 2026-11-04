#include "core/portable/coreparaminfo.h"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelComponent.hpp"
#include "presonus/reconstruction200/large01_w10.hpp"
#include "presonus/trial08/MixerComponentBase.hpp"
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <new>
#include <vector>
static std::uintptr_t trackedAllocation = 0;
static int trackedFrees = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  const bool tracked =
      reinterpret_cast<std::uintptr_t>(p) == trackedAllocation &&
      trackedAllocation;
  __real__ZdlPv(p);
  if (tracked)
    ++trackedFrees;
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  const bool tracked =
      reinterpret_cast<std::uintptr_t>(p) == trackedAllocation &&
      trackedAllocation;
  __real__ZdlPvm(p, n);
  if (tracked)
    ++trackedFrees;
}
extern "C" void frontBaseConstruct(
    Presonus::Panel::FrontPanelComponent *,
    Presonus::Mixer::MixerComponentBase *,
    Presonus::Panel::PanelRegistrar
        *) asm("_ZN8Presonus5Panel19FrontPanelComponentC2ERNS_"
               "5Mixer18MixerComponentBaseERNS0_14PanelRegistrarE");
extern "C" void
frontCompleteDestroy(Presonus::Panel::FrontPanelComponent *) asm(
    "_ZN8Presonus5Panel19FrontPanelComponentD1Ev");
extern "C" void frontBaseDestroy(Presonus::Panel::FrontPanelComponent *) asm(
    "_ZN8Presonus5Panel19FrontPanelComponentD2Ev");
extern "C" void
frontDeletingDestroy(Presonus::Panel::FrontPanelComponent *) asm(
    "_ZN8Presonus5Panel19FrontPanelComponentD0Ev");
using namespace Core::Portable;
struct Param : NumericParam, ParamObserverBase {
  Param(const ParamInfo &info)
      : NumericParam(info, true), observationId(info.tag % 4) {
    addObserver(this);
  }
  ~Param() { removeObserver(this); }
  bool inSet = false;
  void paramChanged(Parameter *, int msg) override {
    if (!inSet && msg == Parameter::kChanged)
      std::printf("changed %d\n", observationId);
  }
  int observationId;
  void setValue(float value, bool edit) override {
    unsigned bits;
    std::memcpy(&bits, &value, 4);
    std::printf("set %d %u %d\n", observationId, bits, edit);
    inSet = true;
    NumericParam::setValue(value, edit);
    inSet = false;
  }
};
struct TestComponent : Core::Portable::Component {
  void add(int tag, float value) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->tag = tag;
    info->minValue = -100.f;
    info->maxValue = 100.f;
    info->defaultValue = value;
    info->deltaValue = 0.01f;
    paramList.add(new Param(*info));
  }
};
struct Deps : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action action, int a,
               int b) override {
    (void)action;
    (void)a;
    (void)b;
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
struct DestroyObserver : Core::Portable::ParamObserverBase {
  int destroyed = 0;
  void paramChanged(Core::Portable::Parameter *, int message) override {
    if (message == Core::Portable::Parameter::kDestroyed)
      ++destroyed;
  }
};
int main(int argc, char **argv) {
  if (argc < 9 || argc > 12)
    return 2;
  const int id = std::atoi(argv[1]);
  const int arg1 = std::atoi(argv[2]);
  const float value = std::strtof(argv[3], nullptr);
  const float paramValue = std::strtof(argv[4], nullptr);
  const int count = std::atoi(argv[5]);
  const int tag = std::atoi(argv[6]);
  const bool executing = std::atoi(argv[7]);
  const int mode = std::atoi(argv[8]);
  const int optionalCase = argc > 9 ? std::atoi(argv[9]) : 0;
  const int activeIndex = argc > 10 ? std::atoi(argv[10]) : -1;
  const int activeMeter = argc > 11 ? std::atoi(argv[11]) : 0;
  if (id == 104) {
    DestroyObserver observer;
    {
      Core::Portable::Component providerOnly("provider-oracle");
      static const Core::Portable::ParamInfo info =
          PARAM_TOGGLE(77, "provider", 0, nullptr, 0);
      providerOnly.addParameters(&info, 1);
      providerOnly.getParameterByTag(77)->addObserver(&observer);
    }
    std::printf("provider_cleanup %d\n", observer.destroyed);
    return 0;
  }
  if (id == 15 || id == 17 || id == 18 || id == 19 || id == 20) {
    Presonus::Mixer::MixerComponentBase mixer;
    presonus::panel_binding::PanelRegistrarPortState registrarState;
    Presonus::Panel::PanelRegistrar registrar(registrarState);
    DestroyObserver observer;
    void *storage =
        ::operator new(sizeof(Presonus::Panel::FrontPanelComponent));
    auto *object = static_cast<Presonus::Panel::FrontPanelComponent *>(storage);
    if (id == 15)
      frontBaseConstruct(object, &mixer, &registrar);
    else
      new (storage) Presonus::Panel::FrontPanelComponent(mixer, registrar);
    auto &state = object->portableFrontState();
    auto &base = object->portableState();
    if (base.mixer != &mixer || base.registrar != &registrar ||
        state.panelParameters != &base.component || state.heldButton != -1 ||
        state.panelMode || state.copyActive || state.fatChannelDirty ||
        state.constructorWord164 != 11 || state.mixSelections.count() ||
        state.pasteSelections.count())
      return 10;
    if (base.component.countParameters() != 136)
      return 11;
    auto *first = base.component.getParameterByTag(1);
    if (!first)
      return 12;
    first->addObserver(&observer);
    trackedAllocation = reinterpret_cast<std::uintptr_t>(object);
    trackedFrees = 0;
    if (id == 15 || id == 19) {
      std::printf("front_ctor 136 1 0 11 -1 0 0\n");
      for (int index = 0; index < base.component.countParameters(); ++index) {
        auto *parameter = base.component.getParameterAt(index);
        auto bits = [](float value) {
          std::uint32_t n;
          std::memcpy(&n, &value, 4);
          return n;
        };
        std::printf("param %d %d %d %u %u %u ", index, parameter->getTag(),
                    parameter->getType(), bits(parameter->getMin()),
                    bits(parameter->getMax()), bits(parameter->getDefault()));
        for (auto *name =
                 reinterpret_cast<const unsigned char *>(parameter->getName());
             *name; ++name)
          std::printf("%02x", *name);
        std::printf("\n");
      }
    }
    if (id == 18)
      frontBaseDestroy(object);
    else if (id == 20)
      frontDeletingDestroy(object);
    else
      frontCompleteDestroy(object);
    if (observer.destroyed != 1 || trackedFrees != (id == 20 ? 1 : 0))
      return 13;
    if (id == 17 || id == 18 || id == 20)
      std::printf("front_cleanup %d %d\n", observer.destroyed, trackedFrees);
    trackedAllocation = 0;
    if (id != 20)
      ::operator delete(storage);
    return 0;
  }
  if (id == 4 || id == 14) {
    Presonus::Mixer::MixerComponentBase mixer;
    presonus::panel_binding::PanelRegistrarPortState registrarState;
    Presonus::Panel::PanelRegistrar registrar(registrarState);
    DestroyObserver observer;
    {
      Presonus::Panel::PanelComponent panelObject(mixer, registrar);
      auto &p = panelObject.portableState();
      if (p.mixer != &mixer || p.registrar != &registrar ||
          std::strcmp(p.component.getName(), "panel") ||
          !p.component.feedbackNeeded())
        return 4;
      if (p.active || p.embeddedHandlerState !=
                          std::array<std::int32_t, 5>{30, 0, -1, 0, 0})
        return 8;
      for (auto *timer : {&p.encoderTimer, &p.buttonTimer}) {
        auto ts = presonus::timing::DelayTimerAccess::get(*timer);
        if (ts.start || ts.duration != 1000 || ts.elapsed || ts.executing)
          return 5;
      }
      bool threw = false;
      try {
        panelObject.activateAll();
      } catch (const std::logic_error &) {
        threw = true;
      }
      if (!threw)
        return 6;
      static const Core::Portable::ParamInfo info =
          PARAM_TOGGLE(77, "lifecycle", 0, nullptr, 0);
      p.component.addParameters(&info, 1);
      p.component.getParameterByTag(77)->addObserver(&observer);
      if (id == 14)
        std::printf("panel_ctor panel 1 1000 1000 0 0 30 0 -1 0 0\n");
    }
    if (observer.destroyed != 1)
      return 7;
    if (id == 4)
      std::printf("panel_cleanup 1\n");
    return 0;
  }
  TestComponent settings, panel, scene;
  for (int i = 0; i <= 10; ++i) {
    if (!((optionalCase == 2 && i == 8) || (optionalCase == 3 && i == 1)))
      panel.add(i, activeMeter ? (i == activeMeter ? paramValue : 0.f)
                               : paramValue);
    scene.add(i, paramValue);
  }
  if (arg1 > 10)
    panel.add(arg1, paramValue);
  presonus::frontpanel_port::State state(settings);
  state.panelParameters = &panel;
  state.sceneParameters = &scene;
  state.storingParameters = optionalCase == 1 ? nullptr : &panel;
  state.panelMode = mode;
  for (int i = 0; i < 2; ++i) {
    state.auxChannels.add(reinterpret_cast<Presonus::Mixer::ChannelComponent *>(
        0x720000 + i * 0x100));
    state.fxChannels.add(reinterpret_cast<Presonus::Mixer::ChannelComponent *>(
        0x730000 + i * 0x100));
  }
  std::vector<Param *> selections;
  for (int i = 0; i < count; ++i) {
    auto *info = new ParamInfo{};
    info->type = ParamInfo::kFloat;
    info->tag = tag + i;
    info->minValue = -100;
    info->maxValue = 100;
    info->defaultValue =
        activeIndex >= 0 ? (i == activeIndex ? paramValue : 0.f) : paramValue;
    info->deltaValue = 0.01f;
    auto *p = new Param(*info);
    p->observationId = i;
    selections.push_back(p);
    state.mixSelections.add(p);
  }
  (void)executing;
  Deps deps;
  Presonus::Panel::FrontPanelComponent object(state, deps);
  switch (id) {
  case 1:
    object.linkChanged();
    break;
  case 5:
    object.notifyStoring(arg1);
    break;
  case 7:
    object.doMix(arg1, value);
    break;
  case 12:
    std::printf("return %llu\n", static_cast<unsigned long long>(
                                     reinterpret_cast<std::uintptr_t>(
                                         object.getMixModeChannel())));
    break;
  case 13:
    std::printf("return %d\n", object.getMeterMode());
    break;
  default:
    return 3;
  }
  if (id == 1 || id == 7)
    std::printf("dirty %d\n", state.fatChannelDirty);
  for (auto *p : selections)
    delete p;
}
