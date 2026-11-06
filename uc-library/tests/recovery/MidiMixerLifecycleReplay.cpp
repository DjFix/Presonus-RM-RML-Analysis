#include "presonus/MackieControlComponent.hpp"
#include "presonus/panel/switch_control.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
using Presonus::Surface::MidiMixerHandler;
using Presonus::Surface::PanelRegistrar;
namespace {
std::vector<std::string> trace;
const Component *localWatch;
const Parameter *normalWatch;
const void *handlerWatch;
PanelRegistrar *registrarWatch;
bool watching = false;
std::vector<MidiMixerHandler *> cleanupRegistry, registryBefore;
int childDestroyed = 0, parameterDestroyed = 0;
IParamObserver *installedObserver;
struct Local : Component {
  void add(Parameter *p) { paramList.add(p); }
  void remove(Parameter *p) { paramList.remove(p); }
};
struct Child : Component {
  ~Child() { ++childDestroyed; }
};
struct Output : StringParam {
  using StringParam::StringParam;
  ~Output() { ++parameterDestroyed; }
};
struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override {}
  bool recordParameterPresent() override { return false; }
  float recordParameterValue() override { std::abort(); }
  void updateRecordMapping(bool) override {}
  bool idleSlotPresent(unsigned) override { return false; }
  void invokeIdleSlot(unsigned) override { std::abort(); }
};
struct Controller : Presonus::IMappingController {
  int getModifiers() const override { throw 1; }
  int getRadioValue(int, int) const override { throw 1; }
  int getBankScrollingOffset() const override { throw 1; }
  Parameter *getParamByTag(int) const override { throw 1; }
  Parameter *getMainScreenParamByTag(int) const override { throw 1; }
  bool isDisplayEncoderLocked() const override { throw 1; }
  bool areFadersLockedToMainMix() const override { throw 1; }
  void encoderChanged(int) const override { throw 1; }
  void onSelectedChannelChanged() override { throw 1; }
  void selectedChannelUpdated() override { throw 1; }
  void setRadioGroup(int, int, int, bool) override { throw 1; }
  void onDeviceDisconnected() override { throw 1; }
};
void observeDelete(void *p) {
  if (watching && p == handlerWatch)
    trace.push_back("delete");
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  observeDelete(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  observeDelete(p);
  __real__ZdlPvm(p, size);
}
extern "C" Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
extern "C" Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *c,
                                                         int t) {
  if (watching && t == 0xa007)
    trace.push_back("lookup");
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(c, t);
}
extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (p == normalWatch)
    installedObserver = o;
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(p, o);
}
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  if (watching && p == normalWatch) {
    assert(o == installedObserver);
    assert(registrarWatch->countMidiHandlers() ==
           static_cast<int>(registryBefore.size()));
    for (unsigned i = 0; i < registryBefore.size(); ++i)
      assert(registrarWatch->getMidiHandler(i) == registryBefore[i]);
    trace.push_back("remove");
  }
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
extern "C" void __real__ZN4Core8Portable9ComponentD2Ev(Component *);
extern "C" void __wrap__ZN4Core8Portable9ComponentD2Ev(Component *c) {
  if (watching && c == localWatch) {
    trace.push_back("cleanup");
    // Registry removal must already have happened before real CCL cleanup.
    assert(registrarWatch);
    for (int i = 0; i < registrarWatch->countMidiHandlers(); ++i)
      cleanupRegistry.push_back(registrarWatch->getMidiHandler(i));
  }
  __real__ZN4Core8Portable9ComponentD2Ev(c);
}
extern "C" void
destroy0(MidiMixerHandler *) asm("_ZN8Presonus7Surface16MidiMixerHandlerD0Ev");
extern "C" void
destroy1(MidiMixerHandler *) asm("_ZN8Presonus7Surface16MidiMixerHandlerD1Ev");
extern "C" void
destroy2(MidiMixerHandler *) asm("_ZN8Presonus7Surface16MidiMixerHandlerD2Ev");
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "guards") {
    Services services;
    presonus::surface::midi_port::State state;
    PanelRegistrar registrar;
    Component normal;
    {
      MidiMixerHandler handler(state, services);
      bool caught = false;
      try {
        handler.initializeOwnedParameters(std::make_unique<Component>(),
                                          registrar);
      } catch (const std::logic_error &) {
        caught = true;
      }
      assert(caught && registrar.countMidiHandlers() == 0);
      state.normalParameters = &normal;
      caught = false;
      try {
        handler.initializeOwnedParameters(nullptr, registrar);
      } catch (const std::logic_error &) {
        caught = true;
      }
      assert(caught && registrar.countMidiHandlers() == 0);
      handler.initializeOwnedParameters(std::make_unique<Component>(),
                                        registrar);
      caught = false;
      try {
        handler.initializeOwnedParameters(std::make_unique<Component>(),
                                          registrar);
      } catch (const std::logic_error &) {
        caught = true;
      }
      assert(caught && registrar.countMidiHandlers() == 1);
    }
    assert(registrar.countMidiHandlers() == 0 &&
           state.localParameters == nullptr);
    std::cout
        << "PASS owned initialization guards and borrowed-only compatibility\n";
    return 0;
  }
  if (argc < 4)
    return 2;
  const int variant = std::stoi(argv[1]), present = std::stoi(argv[2]);
  const bool missingObserver = argc > 4 && std::string(argv[4]) == "missing";
  ParamInfo normalInfo = PARAM_STRING(0xa007, "time", 0);
  ParamInfo outputInfo = PARAM_STRING(2, "output", 0);
  ParamInfo stepInfo =
      PARAM_FLOAT(1, "step", 0, 1, 0, 1, nullptr, nullptr, 0, 0);
  Local normalParameters, alternateParameters, prior;
  StringParam normalParameter(normalInfo);
  normalWatch = &normalParameter;
  if (present)
    normalParameters.add(&normalParameter);
  Services services;
  presonus::surface::midi_port::State state;
  state.normalParameters = &normalParameters;
  state.alternateParameters = &alternateParameters;
  state.localParameters = &prior;
  Presonus::MackieControlComponent normal, alternate;
  state.normalMackie = &normal;
  state.alternateMackie = &alternate;
  Controller controller;
  state.controller = &controller;
  std::vector<std::vector<unsigned char>> midi;
  normal.model.midiSink = [&](const unsigned char *p, unsigned n, unsigned) {
    midi.emplace_back(p, p + n);
  };
  normal.model.addMapping(0x4300, 23);
  normal.model.addMapping(7, 42);
  PanelRegistrar registrar;
  registrarWatch = &registrar;
  MidiMixerHandler other(state, services), third(state, services);
  void *storage = ::operator new(sizeof(MidiMixerHandler));
  auto *handler = new (storage) MidiMixerHandler(state, services);
  handlerWatch = handler;
  auto local = std::make_unique<Local>();
  auto *output = new Output(outputInfo);
  local->add(output);
  local->add(new NumericParam(stepInfo));
  local->addChild(new Child);
  localWatch = local.get();
  handler->initializeOwnedParameters(std::move(local), registrar);
  assert(state.localParameters == localWatch);
  if (present) {
    normalParameter.fromString("12345678", false);
    assert(std::string(output->getText().str()) == "123:45:67:8");
    assert(installedObserver);
    if (missingObserver)
      normalParameter.removeObserver(installedObserver);
  }
  Presonus::Panel::ControlRegistrar controls;
  ParamInfo buttonInfo =
      PARAM_INT(7, "button", 0, 1, 0, nullptr, nullptr, 0, 0);
  NumericParam button(buttonInfo);
  Presonus::Panel::SwitchControl sw(1, 0, false);
  presonus::panel::ControlAccess::parameter(sw) = &button;
  assert(registrar.addMidiHandler(nullptr));
  registrar.dispatchMidiSwitch(controls, 0, 0, true, &sw);
  registrar.dispatchMidiEncoder(controls, 0, 5, nullptr);
  assert(midi.size() == 2);
  assert(registrar.removeMidiHandler(nullptr));
  assert((midi[0] == std::vector<unsigned char>{144, 42, 127}));
  assert((midi[1] == std::vector<unsigned char>{176, 23, 1}));
  // Replace automatic entry with exact native list, including missing target,
  // duplicate target and null entries. All non-null sentinels are live
  // handlers.
  assert(registrar.removeMidiHandler(handler));
  for (char c : std::string(argv[3])) {
    MidiMixerHandler *p = c == '0'   ? nullptr
                          : c == '1' ? handler
                          : c == '2' ? &other
                                     : &third;
    assert(registrar.addMidiHandler(p));
  }
  for (int i = 0; i < registrar.countMidiHandlers(); ++i)
    registryBefore.push_back(registrar.getMidiHandler(i));
  trace.clear();
  watching = true;
  if (variant == 0)
    destroy0(handler);
  else if (variant == 1)
    destroy1(handler);
  else if (variant == 2)
    destroy2(handler);
  else
    return 3;
  watching = false;
  assert(state.localParameters == &prior);
  assert(childDestroyed == 1 && parameterDestroyed == 1);
  for (const auto &s : trace)
    std::cout << s << ';';
  std::cout << '|';
  assert(cleanupRegistry.size() ==
         static_cast<unsigned>(registrar.countMidiHandlers()));
  for (int i = 0; i < registrar.countMidiHandlers(); ++i) {
    auto *p = cleanupRegistry[i];
    assert(p == registrar.getMidiHandler(i));
    std::cout << (p == nullptr ? 0 : p == handler ? 1 : p == &other ? 2 : 3);
  }
  std::cout << '\n';
  // Duplicate entries are not ownership. Clear leftover dangling registrations
  // before invoking live registry again; native removes only the first entry.
  while (registrar.removeMidiHandler(handler)) {
  }
  while (registrar.removeMidiHandler(&other)) {
  }
  while (registrar.removeMidiHandler(&third)) {
  }
  assert(registrar.getMidiHandler(-1) == nullptr);
  assert(registrar.getMidiHandler(registrar.countMidiHandlers()) == nullptr);
  assert(!registrar.removeMidiHandler(handler));
  auto messages = midi.size();
  registrar.dispatchMidiSwitch(controls, 0, 0, false, &sw);
  registrar.dispatchMidiEncoder(controls, 0, 5, nullptr);
  assert(midi.size() == messages);
  if (present) {
    // A real subsequent notification must not reach the destroyed bridge.
    normalParameter.fromString("87654321", false);
    normalParameters.remove(&normalParameter);
  }
  if (variant != 0)
    ::operator delete(storage);
}
