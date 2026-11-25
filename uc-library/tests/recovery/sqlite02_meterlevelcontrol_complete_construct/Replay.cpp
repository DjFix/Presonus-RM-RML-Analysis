#include "presonus/panel/meter_level_control.hpp"
#include "presonus/surface_panel/MeterControl.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>

using Presonus::Panel::Control;
using Presonus::Panel::MeterControl;
using Presonus::Panel::MeterLevelControl;
using CA = presonus::panel::ControlAccess;
using MA = presonus::panel::MeterLevelControlAccess;
using BA = presonus::surface_panel_port::MeterControlAccess;
using Core::Portable::IParamObserver;
using Core::Portable::Parameter;

namespace {
struct Derived : MeterLevelControl {
  using MeterLevelControl::MeterLevelControl;
};

void *receiver = nullptr;
void *timer = nullptr;
Parameter *params[3]{};
bool recording = false;

void deallocation(void *pointer) {
  if (recording && pointer == receiver)
    std::cout << " delete_receiver";
  if (recording && pointer == timer)
    std::cout << " delete_timer";
}

void construct(MeterLevelControl &value) {
  auto &base = static_cast<MeterControl &>(value);
  Control &control = value;
  const bool usesOverride = BA::overrideCount(base) != nullptr;
  std::cout << (control.castTo(0x4d4c436c) == &value &&
                dynamic_cast<MeterLevelControl *>(&control) == &value)
            << ' ' << CA::tag(value) << ' ' << CA::lastLevel(value) << ' '
            << (CA::parameter(value) != nullptr) << ' '
            << (CA::altParameter(value) != nullptr) << ' '
            << (CA::tertiaryParameter(value) != nullptr) << ' '
            << (CA::io(value) != nullptr) << ' ' << usesOverride << ' '
            << BA::direction(base) << ' ' << value.getParameterMode() << ' '
            << MA::clipActive(value);
}

[[gnu::noipa]] void destroyVirtual(Control *value) { delete value; }

void lifecycle(std::string_view operation, bool withTimer) {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  Core::Portable::NumericParam first(info), second(info), third(info);
  params[0] = &first;
  params[1] = &second;
  params[2] = &third;
  alignas(Derived) std::byte storage[sizeof(Derived)];
  auto *value = operation == "base_destroy"       ? new (storage) Derived(23)
                : operation == "deleting_destroy" ? new MeterLevelControl(23)
                                                  : new (storage)
                                                        MeterLevelControl(23);
  receiver = value;
  value->Control::setParameter(&first, 0);
  value->Control::setAltParameter(&second);
  value->Control::setTertiaryParameter(&third);
  if (withTimer) {
    value->startTimer(10.f, 23);
    if (!value->isTimerRunning(23))
      std::abort();
    timer = CA::timers().at(0);
  }
  recording = true;
  if (operation == "deleting_destroy")
    destroyVirtual(value);
  else if (operation == "base_destroy")
    static_cast<Derived *>(value)->~Derived();
  else
    value->~MeterLevelControl();
  recording = false;
  receiver = timer = nullptr;
  if (CA::timers().count() != 0)
    std::abort();
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  deallocation(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  deallocation(pointer);
  __real__ZdlPvm(pointer, size);
}

extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *parameter, IParamObserver *observer) {
  if (recording &&
      observer == static_cast<IParamObserver *>(
                      static_cast<MeterLevelControl *>(receiver))) {
    for (int index = 0; index < 3; ++index)
      if (params[index] == parameter)
        std::cout << " unregister_" << index;
  }
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      parameter, observer);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view operation = argv[1];
  const int arg = static_cast<int>(std::strtol(argv[2], nullptr, 10));
  if (operation == "cast_type") {
    MeterLevelControl value(23);
    Control &control = value;
    auto *result = control.castTo(arg);
    const void *view = &value;
    if (arg == 0x4d43746c)
      view = static_cast<MeterControl *>(&value);
    if (arg == 0x4374726c)
      view = static_cast<Control *>(&value);
    if (result && result != view)
      return 1;
    std::cout << (result != nullptr);
  } else if (operation == "get_parameter_mode") {
    MeterLevelControl value(23);
    if (arg != 0)
      MA::parameterMode(value) = arg;
    const Control &control = value;
    std::cout << control.getParameterMode();
  } else if (operation == "base_construct") {
    Derived value(arg);
    construct(value);
  } else if (operation == "complete_construct") {
    MeterLevelControl value(arg);
    construct(value);
  } else {
    lifecycle(operation, arg != 0);
  }
  std::cout << '\n';
}
