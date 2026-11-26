#include "presonus/panel/meter_peak_control.hpp"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>

using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::MeterPeakControl;

namespace presonus::panel {
struct MeterPeakControlAccess {
  static void printInitialState(MeterPeakControl &control) {
    std::cout << ControlAccess::lastLevel(control) << ' '
              << (ControlAccess::parameter(control) != nullptr) << ' '
              << (ControlAccess::altParameter(control) != nullptr) << ' '
              << (ControlAccess::tertiaryParameter(control) != nullptr) << ' '
              << (ControlAccess::io(control) != nullptr) << ' '
              << ControlAccess::tag(control) << ' ' << control.peakOffset_
              << ' ' << (control.scaleTable_ != nullptr) << ' '
              << control.scaleMode_ << '\n';
  }
};
} // namespace presonus::panel

#ifndef METER_PEAK_CASE
#error "Select the sealed MeterPeakControl replay case"
#endif

namespace {
constexpr int peakType = 0x5043746c;
constexpr int meterType = 0x4d43746c;
constexpr int controlType = 0x4374726c;

void validateDispatch(MeterPeakControl &value) {
  Control &control = value;
  if (control.castTo(peakType) != &value ||
      control.castTo(meterType) != &value ||
      control.castTo(controlType) != &control || control.castTo(0))
    std::abort();
}

struct Derived : MeterPeakControl {
  explicit Derived(int tag) : MeterPeakControl(tag) {}
};

#if METER_PEAK_CASE == 2 || METER_PEAK_CASE == 3
using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
void *receiver;
void *timer;
Parameter *observedParameter;
IParamObserver *observedOwner;
bool receiverFreed;
bool timerFreed;
bool observerRemoved;

struct Survivor final : Core::Portable::ParamObserverBase {
  int seen = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      ++seen;
  }
};
#endif
} // namespace

#if METER_PEAK_CASE == 2 || METER_PEAK_CASE == 3
namespace {
void observeDelete(void *pointer) {
  if (receiver && pointer == receiver) {
    if (receiverFreed || (timer != nullptr && !(timerFreed && observerRemoved)))
      std::abort();
    receiverFreed = true;
  } else if (timer && pointer == timer) {
    if (timerFreed)
      std::abort();
    timerFreed = true;
  }
}
#if METER_PEAK_CASE == 3
[[gnu::noipa]] void deleteThroughControl(Control *control) { delete control; }
#endif
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *pointer) {
  observeDelete(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  observeDelete(pointer);
  __real__ZdlPvm(pointer, size);
}

extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *parameter, IParamObserver *observer) {
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      parameter, observer);
  if (parameter == observedParameter && observer == observedOwner) {
    if (observerRemoved || !timerFreed)
      std::abort();
    observerRemoved = true;
  }
}
#endif

int main() {
#if METER_PEAK_CASE == 0 || METER_PEAK_CASE == 1
  for (int tag : {0, 19, -3, std::numeric_limits<int>::min(),
                  std::numeric_limits<int>::max()}) {
#if METER_PEAK_CASE == 0
    MeterPeakControl value(tag);
#else
    Derived value(tag);
#endif
    validateDispatch(value);
    presonus::panel::MeterPeakControlAccess::printInitialState(value);
  }
#elif METER_PEAK_CASE == 4
  MeterPeakControl value(19);
  Control &control = value;
  for (int type :
       {0, -1, peakType - 1, peakType, peakType + 1, meterType - 1, meterType,
        meterType + 1, controlType - 1, controlType, controlType + 1}) {
    void *result = control.castTo(type);
    if (result && result != (type == controlType ? static_cast<void *>(&control)
                                                 : static_cast<void *>(&value)))
      return 1;
    std::cout << (result != nullptr) << '\n';
  }
#else
  for (bool populated : {false, true}) {
    Core::Portable::ParamInfo info{};
    Core::Portable::NumericParam parameter(info);
    Survivor survivorObserver;
    Control survivor(-41);
#if METER_PEAK_CASE == 2
    alignas(MeterPeakControl) unsigned char storage[sizeof(MeterPeakControl)];
    auto *owner = new (storage) MeterPeakControl(41);
#else
    auto *owner = new MeterPeakControl(41);
#endif
    validateDispatch(*owner);
    receiver = owner;
    observedOwner = owner;
    receiverFreed = timerFreed = observerRemoved = false;
    if (populated) {
      // Match the native destructor oracle: seed observer state directly.
      ControlAccess::parameter(*owner) = &parameter;
      parameter.addObserver(owner);
      parameter.addObserver(&survivorObserver);
      owner->startTimer(1.f, 1);
      survivor.startTimer(1.f, 2);
      if (ControlAccess::timers().count() != 2)
        return 1;
      timer = ControlAccess::timers().at(0);
      observedParameter = &parameter;
    }
#if METER_PEAK_CASE == 2
    owner->~MeterPeakControl();
#else
    deleteThroughControl(owner);
#endif
    receiver = timer = nullptr;
    observedParameter = nullptr;
    observedOwner = nullptr;
    const auto count = ControlAccess::timers().count();
    if (populated) {
      if (!timerFreed || !observerRemoved || !survivor.isTimerRunning(2) ||
          count != 1)
        return 1;
      parameter.setValueFast(0.75f);
      if (survivorObserver.seen != 1)
        return 1;
      parameter.removeObserver(&survivorObserver);
    }
    std::cout << receiverFreed << ' ' << count << ' '
              << (populated && observerRemoved && survivorObserver.seen == 1)
              << '\n';
  }
#endif
}
