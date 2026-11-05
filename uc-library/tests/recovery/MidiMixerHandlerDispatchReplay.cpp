#include "presonus/MackieControlComponent.hpp"
#include "presonus/panel/switch_control.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
using namespace Core::Portable;
namespace {
std::vector<std::string> trace;
Presonus::MackieControlComponent *normal, *alternate;
int which(const void *p) { return p == alternate || p == &alternate->model; }
struct Local : Component {
  void add(Parameter *p) { paramList.add(p); }
};
struct Number : NumericParam {
  using NumericParam::NumericParam;
  bool originalPresent = true;
  Parameter *getOriginal() override {
    trace.push_back("original " + std::to_string(originalPresent));
    return originalPresent ? this : nullptr;
  }
  float getValue() const override {
    unsigned bits;
    std::memcpy(&bits, &value, 4);
    trace.push_back("value " + std::to_string(bits));
    return NumericParam::getValue();
  }
  void raw(unsigned bits) { std::memcpy(&value, &bits, 4); }
};
struct Services : presonus::surface::midi_port::Services {
  void setDefaultColor(const std::string &) override {
    trace.push_back("colors");
  }
  bool recordParameterPresent() override { return false; }
  float recordParameterValue() override {
    throw std::logic_error("unexpected record");
  }
  void updateRecordMapping(bool) override {}
  bool idleSlotPresent(unsigned) override { return false; }
  void invokeIdleSlot(unsigned) override {
    throw std::logic_error("unexpected idle");
  }
};
// Boundary double only: target methods store/test this borrowed interface and
// never invoke it. Every unexpected call fails instead of inventing behavior.
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
} // namespace
extern "C" Presonus::MackieControlModel *
__real__ZN8Presonus22MackieControlComponent8getModelEv(
    Presonus::MackieControlComponent *);
extern "C" Presonus::MackieControlModel *
__wrap__ZN8Presonus22MackieControlComponent8getModelEv(
    Presonus::MackieControlComponent *p) {
  trace.push_back("getModel " + std::to_string(which(p)));
  return __real__ZN8Presonus22MackieControlComponent8getModelEv(p);
}
extern "C" void __real__ZN8Presonus18MackieControlModel17releaseAllButtonsEv(
    Presonus::MackieControlModel *);
extern "C" void __wrap__ZN8Presonus18MackieControlModel17releaseAllButtonsEv(
    Presonus::MackieControlModel *p) {
  trace.push_back("release " + std::to_string(which(p)));
  __real__ZN8Presonus18MackieControlModel17releaseAllButtonsEv(p);
}
extern "C" bool __real__ZN8Presonus18MackieControlModel14setButtonStateEib(
    Presonus::MackieControlModel *, int, bool);
extern "C" bool __wrap__ZN8Presonus18MackieControlModel14setButtonStateEib(
    Presonus::MackieControlModel *p, int t, bool b) {
  trace.push_back("button " + std::to_string(which(p)) + " " +
                  std::to_string(t) + " " + std::to_string(b));
  return __real__ZN8Presonus18MackieControlModel14setButtonStateEib(p, t, b);
}
extern "C" void __real__ZN8Presonus18MackieControlModel11turnEncoderEii(
    Presonus::MackieControlModel *, int, int);
extern "C" void __wrap__ZN8Presonus18MackieControlModel11turnEncoderEii(
    Presonus::MackieControlModel *p, int t, int d) {
  trace.push_back("encoder " + std::to_string(which(p)) + " " +
                  std::to_string(t) + " " + std::to_string(d));
  __real__ZN8Presonus18MackieControlModel11turnEncoderEii(p, t, d);
}
extern "C" void __real__ZN8Presonus18MackieControlModel14turnScrubwheelEi(
    Presonus::MackieControlModel *, int);
extern "C" void __wrap__ZN8Presonus18MackieControlModel14turnScrubwheelEi(
    Presonus::MackieControlModel *p, int d) {
  trace.push_back("scrub " + std::to_string(which(p)) + " " +
                  std::to_string(d));
  __real__ZN8Presonus18MackieControlModel14turnScrubwheelEi(p, d);
}
extern "C" void
__real__ZN8Presonus7Surface16MidiMixerHandler18setControlsEnabledEb(
    Presonus::Surface::MidiMixerHandler *, bool);
extern "C" void
__wrap__ZN8Presonus7Surface16MidiMixerHandler18setControlsEnabledEb(
    Presonus::Surface::MidiMixerHandler *p, bool b) {
  trace.push_back("enable " + std::to_string(b));
  __real__ZN8Presonus7Surface16MidiMixerHandler18setControlsEnabledEb(p, b);
}
extern "C" Parameter *__real__ZNK8Presonus5Panel7Control12getParameterEv(
    const Presonus::Panel::Control *);
extern "C" Parameter *__wrap__ZNK8Presonus5Panel7Control12getParameterEv(
    const Presonus::Panel::Control *p) {
  auto *v = __real__ZNK8Presonus5Panel7Control12getParameterEv(p);
  trace.push_back("parameter " + std::to_string(v != nullptr));
  return v;
}
extern "C" Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
extern "C" Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *p,
                                                         int tag) {
  auto *v = __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
  trace.push_back("lookup " + std::to_string(v != nullptr));
  return v;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "guards") {
    presonus::surface::midi_port::State state;
    Services services;
    Presonus::Surface::MidiMixerHandler handler(state, services);
    bool caught = false;
    try {
      handler.disconnect();
    } catch (const std::logic_error &) {
      caught = true;
    }
    if (!caught)
      return 10;
    Controller controller;
    Presonus::Panel::ControlRegistrar registrar;
    handler.setController(&controller);
    caught = false;
    try {
      handler.encoderChanged(registrar, 0, 1, nullptr);
    } catch (const std::logic_error &) {
      caught = true;
    }
    if (!caught)
      return 11;
    Presonus::MackieControlComponent a, b, replacement;
    normal = &a;
    alternate = &replacement;
    state.normalMackie = &a;
    state.alternateMackie = &b;
    caught = false;
    try {
      handler.disconnect();
    } catch (const std::logic_error &) {
      caught = true;
    }
    if (!caught)
      return 12;
    std::array<unsigned char, 44> terminator{};
    state.controlDescriptions = &terminator;
    state.colorControls = {"color"};
    a.model.addMapping(1, 42);
    a.model.buttonStates[0] = 1;
    a.model.buttonRelease = [&](int tag, bool down) {
      a.model.setButtonState(tag, down);
      state.alternateMackie = &replacement;
    };
    a.model.faderRelease = [&](int tag, bool down) {
      a.model.touchFader(tag, down);
    };
    replacement.model.addMapping(2, 43);
    replacement.model.buttonStates[0] = 1;
    replacement.model.buttonRelease = [&](int tag, bool down) {
      replacement.model.setButtonState(tag, down);
    };
    replacement.model.faderRelease = [&](int tag, bool down) {
      replacement.model.touchFader(tag, down);
    };
    state.accumulation.fill(123);
    trace.clear();
    handler.setController(nullptr);
    if (state.controller || a.model.buttonStates[0] ||
        replacement.model.buttonStates[0])
      return 13;
    for (auto v : state.accumulation)
      if (v)
        return 14;
    // The originally supplied alternate has no release bindings: success proves
    // the replacement was fetched after the normal model's actual release.
    std::cout << "three explicit missing-binding guards and live alternate "
                 "mutation passed\n";
    return 0;
  }

  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    int method, ctrl, index, delta, present, flag, pressed, orig, incoming;
    unsigned acc, bits;
    if (!(in >> method >> ctrl >> index >> delta >> acc >> present >> bits >>
          flag >> pressed >> orig >> incoming))
      return 2;
    Presonus::MackieControlComponent a, b;
    normal = &a;
    alternate = &b;
    std::vector<std::vector<unsigned char>> messages;
    for (auto *component : {&a, &b}) {
      auto &m = component->model;
      m.addMapping(index, 42);
      m.buttonStates[0] = 1;
      m.touched.fill(1);
      m.midiSink = [&](const unsigned char *data, unsigned size,
                       unsigned port) {
        if (port != 0)
          std::abort();
        messages.emplace_back(data, data + size);
      };
      m.buttonRelease = [&m](int tag, bool down) {
        m.setButtonState(tag, down);
      };
      m.faderRelease = [&m](int tag, bool down) { m.touchFader(tag, down); };
    }
    ParamInfo info =
        PARAM_FLOAT(1, "mode", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
    Local local;
    auto *mode = new Number(info);
    mode->raw(bits);
    if (present)
      local.add(mode);
    else
      delete mode;
    ParamInfo switchInfo =
        PARAM_FLOAT(0, "switch", 0, 1, 0, 1, nullptr, nullptr, 0, 0);
    switchInfo.tag = index;
    switchInfo.flags = flag;
    Number number(switchInfo);
    number.originalPresent = orig;
    Presonus::Panel::SwitchControl control(1, 0, false);
    presonus::panel::ControlAccess::parameter(control) =
        present ? &number : nullptr;
    presonus::surface::midi_port::State state;
    state.normalMackie = &a;
    state.alternateMackie = &b;
    state.localParameters = &local;
    std::array<unsigned char, 44> terminator{};
    state.controlDescriptions = &terminator;
    state.colorControls = {"color"};
    state.accumulation.fill(acc);
    Controller controller;
    state.controller = ctrl ? &controller : nullptr;
    Services services;
    Presonus::Surface::MidiMixerHandler handler(state, services);
    Presonus::Panel::ControlRegistrar registrar;
    trace.clear();
    if (method == 1)
      handler.disconnect();
    if (method == 2)
      handler.setController(incoming ? &controller : nullptr);
    if (method == 3)
      handler.switchChanged(registrar, -100, 99, pressed, &control);
    if (method == 4)
      handler.encoderChanged(registrar, index, delta, nullptr);
    if (method == 1 || (method == 2 && !incoming)) {
      for (auto *component : {&a, &b}) {
        if (component->model.buttonStates[0] != 0)
          std::abort();
        for (auto v : component->model.touched)
          if (v)
            std::abort();
      }
      if (messages.empty())
        std::abort();
    }
    // Release forwarding is actual production provider behavior. Its nested
    // setButtonState calls are outside the native target boundary trace.
    bool releasing = false;
    for (const auto &event : trace) {
      if (event.rfind("release ", 0) == 0)
        releasing = true;
      if (event.rfind("getModel ", 0) == 0 || event.rfind("enable ", 0) == 0)
        releasing = false;
      if (releasing && event.rfind("button ", 0) == 0)
        continue;
      std::cout << event << ';';
    }
    std::cout << '|';
    for (auto value : state.accumulation)
      std::cout << value << ' ';
    std::cout << "|" << (state.controller != nullptr) << "|";
    for (const auto &message : messages) {
      for (auto byte : message)
        std::cout << unsigned(byte) << ',';
      std::cout << ';';
    }
    std::cout << '\n';
    presonus::panel::ControlAccess::parameter(control) = nullptr;
  }
}
