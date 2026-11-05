#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <new>
#include <string>
using Rack = Presonus::Panel::RackPanelComponent;
namespace {
void *watched[5]{};
Presonus::DelayTimer *timers[4]{};
int events[32]{}, total = 0;
bool capture = false;
void event(int n) {
  if (capture) {
    assert(total < 32);
    events[total++] = n;
  }
}
void observe(void *p) {
  if (p && capture)
    for (int i = 0; i < 5; ++i)
      if (p == watched[i])
        event(i);
}
} // namespace
void operator delete(void *p) noexcept {
  observe(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
extern "C" void
realTimer(Presonus::DelayTimer *) asm("__real__ZN8Presonus10DelayTimerD1Ev");
extern "C" void
wrapTimer(Presonus::DelayTimer *) asm("__wrap__ZN8Presonus10DelayTimerD1Ev");
extern "C" void wrapTimer(Presonus::DelayTimer *p) {
  for (int i = 0; i < 4; ++i)
    if (p == timers[i])
      event(10 + i);
  realTimer(p);
}
extern "C" void realBase(Presonus::Panel::PanelComponent *) asm(
    "__real__ZN8Presonus5Panel14PanelComponentD2Ev");
extern "C" void wrapBase(Presonus::Panel::PanelComponent *) asm(
    "__wrap__ZN8Presonus5Panel14PanelComponentD2Ev");
extern "C" void wrapBase(Presonus::Panel::PanelComponent *p) {
  event(20);
  realBase(p);
}
extern "C" void d0(Rack *) asm("_ZN8Presonus5Panel18RackPanelComponentD0Ev");
extern "C" void d1(Rack *) asm("_ZN8Presonus5Panel18RackPanelComponentD1Ev");
extern "C" void d2(Rack *) asm("_ZN8Presonus5Panel18RackPanelComponentD2Ev");
extern "C" void
c1(Rack *, Presonus::Mixer::MixerComponentBase &,
   Presonus::Panel::PanelRegistrar
       &) asm("_ZN8Presonus5Panel18RackPanelComponentC1ERNS_"
              "5Mixer18MixerComponentBaseERNS0_14PanelRegistrarE");
extern "C" void
c2(Rack *, Presonus::Mixer::MixerComponentBase &,
   Presonus::Panel::PanelRegistrar
       &) asm("_ZN8Presonus5Panel18RackPanelComponentC2ERNS_"
              "5Mixer18MixerComponentBaseERNS0_14PanelRegistrarE");
void parameters(Core::Portable::Component &c) {
  for (int i = 0; i < c.countParameters(); ++i) {
    auto *p = c.getParameterAt(i);
    auto *list = static_cast<Core::Portable::ListParam *>(p);
    std::cout << p->getType() << ' ' << p->getTag() << ' '
              << std::quoted(p->getName()) << ' ' << std::quoted(p->getTitle())
              << ' ' << p->getMin() << ' ' << p->getMax() << ' '
              << p->getDefault() << ' ' << p->getValue() << ' '
              << std::quoted(list->getStringAt(0)) << ' '
              << std::quoted(list->getStringAt(1)) << '\n';
  }
}
int main(int argc, char **argv) {
  assert(argc >= 2);
  std::string mode = argv[1];
  if (mode == "provider") {
    Core::Portable::Component component;
    Core::Portable::ParamInfo infos[5]{};
    std::string names[5], titles[5], off, on;
    const char *strings[5][2];
    std::string labels[5][2];
    for (int i = 0; i < 5; ++i) {
      auto &p = infos[i];
      std::cin >> p.type >> p.tag >> std::quoted(names[i]) >>
          std::quoted(titles[i]) >> p.minValue >> p.maxValue >> p.midValue >>
          p.defaultValue >> p.deltaValue >> p.flags >>
          std::quoted(labels[i][0]) >> std::quoted(labels[i][1]);
      assert(std::cin);
      std::strncpy(p.name, names[i].c_str(), 31);
      p.title = titles[i].c_str();
      strings[i][0] = labels[i][0].c_str();
      strings[i][1] = labels[i][1].c_str();
      p.stringList = strings[i];
    }
    component.addParameters(infos, 5);
    parameters(component);
    return 0;
  }
  Presonus::Mixer::MixerComponentBase mixer;
  presonus::panel_binding::PanelRegistrarPortState port;
  Presonus::Panel::PanelRegistrar registrar(port);
  void *memory = ::operator new(sizeof(Rack));
  auto *rack = static_cast<Rack *>(memory);
  if (mode == "c2")
    c2(rack, mixer, registrar);
  else
    c1(rack, mixer, registrar);
  assert(&rack->portableState().component ==
         static_cast<presonus::panel_port::PanelCore *>(rack));
  assert(!rack->portableState().ownedComponent &&
         rack->portableState().component.feedbackNeeded());
  assert(rack->portableState().mixer == &mixer &&
         rack->portableState().registrar == &registrar);
  assert(rack->mixer == &mixer && rack->permissionFlags == 0 &&
         rack->savedMonitorValue == 0 && rack->panelStatus == 0);
  assert(!rack->monitorRadioParameter && !rack->observedParameter);
  for (auto *t : {&rack->monitorTimer, &rack->cueTimer, &rack->statusTimer,
                  &rack->resetTimer}) {
    auto state = presonus::timing::DelayTimerAccess::get(*t);
    assert(state.start == 0 && state.duration == 1000 && state.elapsed == 0 &&
           state.reciprocal == 1.f / 1000.f && !state.executing);
  }
  if (mode == "c1" || mode == "c2") {
    parameters(*rack);
    d1(rack);
    ::operator delete(memory);
    return 0;
  }
  assert(argc == 3);
  bool filled = std::stoi(argv[2]);
  if (filled) {
    // Real containers free only their arrays, never these borrowed pointers.
    rack->meterLEDs.push_back(
        reinterpret_cast<Presonus::Panel::Control *>(0x1000));
    rack->clipLEDs.push_back(
        reinterpret_cast<Presonus::Panel::Control *>(0x2000));
    rack->phantomLEDs.push_back(
        reinterpret_cast<Presonus::Panel::Control *>(0x3000));
    assert(rack->tasks.add(
        reinterpret_cast<Presonus::Panel::PanelTask *>(0x4000)));
  }
  watched[0] = rack->meterLEDs.storage().getItems();
  watched[1] = rack->clipLEDs.storage().getItems();
  watched[2] = rack->phantomLEDs.storage().getItems();
  watched[3] = rack->tasks.getItems();
  watched[4] = memory;
  timers[0] = &rack->monitorTimer;
  timers[1] = &rack->cueTimer;
  timers[2] = &rack->statusTimer;
  timers[3] = &rack->resetTimer;
  capture = true;
  if (mode == "d0")
    d0(rack);
  else if (mode == "d1")
    d1(rack);
  else {
    assert(mode == "d2");
    d2(rack);
  }
  capture = false;
  for (int i = 0; i < total; ++i)
    std::cout << events[i] << ' ';
  std::cout << '\n';
  if (mode != "d0")
    ::operator delete(memory);
}
