#include "presonus/panel/pan_meter_control.hpp"

#include <cstdlib>
#include <iostream>
#include <new>
#include <string_view>

namespace {
using Core::Portable::IParamObserver;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::MeterLevelControl;
using Presonus::Panel::PanMeterControl;
using presonus::surface_panel_port::MeterControlAccess;

const void *receiver = nullptr;
const void *timer = nullptr;
const void *observer = nullptr;
Parameter *trackedParameters[3]{};
unsigned events = 0;
unsigned actualReleases = 0;
unsigned receiverReleaseAt = 0;
unsigned timerReleaseAt = 0;
unsigned observerMask = 0;
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);

void recordRelease(const void *address) {
  if (address == receiver) {
    ++actualReleases;
    receiverReleaseAt = ++events;
  } else if (address == timer) {
    timerReleaseAt = ++events;
  }
}

extern "C" void __wrap__ZdlPv(void *address) {
  recordRelease(address);
  __real__ZdlPv(address);
}

extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) {
  recordRelease(address);
  __real__ZdlPvm(address, size);
}

extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *param, IParamObserver *who) {
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      param, who);
  if (who == observer) {
    for (unsigned index = 0; index < 3; ++index) {
      if (param == trackedParameters[index]) {
        observerMask |= 1u << index;
        ++events;
      }
    }
  }
}

namespace {
[[gnu::noipa]] void destroyThroughBase(MeterLevelControl *base) { delete base; }

int exercise(int tag, unsigned mask, bool trackedTimer, bool provider,
             bool deleting) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.maxValue = 1.f;
  NumericParam primary(info), alternate(info), tertiary(info);
  trackedParameters[0] = &primary;
  trackedParameters[1] = &alternate;
  trackedParameters[2] = &tertiary;
  alignas(PanMeterControl) unsigned char buffer[sizeof(PanMeterControl)];
  int borrowedCount = 17;
  MeterLevelControl *meter = provider   ? new (buffer) MeterLevelControl(tag)
                             : deleting ? new PanMeterControl(tag)
                                        : new (buffer) PanMeterControl(tag);
  Control *control = meter;
  MeterControlAccess::setState(*meter, &borrowedCount, 1);
  Control other(999);
  other.startTimer(1.f, 9);
  auto &timers = ControlAccess::timers();
  if (timers.count() != 1)
    return 1;
  const auto *otherTimer = timers.at(0);
  // Native destructor oracle directly seeds parameter slots; no IO callback.
  if (mask & 1) {
    ControlAccess::parameter(*control) = &primary;
    primary.addObserver(control);
  }
  if (mask & 2) {
    ControlAccess::altParameter(*control) = &alternate;
    alternate.addObserver(control);
  }
  if (mask & 4) {
    ControlAccess::tertiaryParameter(*control) = &tertiary;
    tertiary.addObserver(control);
  }
  if (trackedTimer)
    control->startTimer(1.f, 8);
  if (timers.count() != 1 + static_cast<int>(trackedTimer))
    return 2;

  receiver = control;
  observer = static_cast<IParamObserver *>(control);
  timer = trackedTimer ? timers.at(1) : nullptr;
  events = actualReleases = receiverReleaseAt = timerReleaseAt = observerMask =
      0;
  if (provider)
    meter->MeterLevelControl::~MeterLevelControl();
  else if (deleting)
    destroyThroughBase(meter);
  else
    static_cast<PanMeterControl *>(meter)->PanMeterControl::~PanMeterControl();
  receiver = observer = timer = nullptr;
  if (timers.count() != 1 || timers.at(0) != otherTimer ||
      borrowedCount != 17 || (timerReleaseAt != (trackedTimer ? 1u : 0u)) ||
      observerMask != mask || (actualReleases != (deleting ? 1u : 0u)) ||
      (receiverReleaseAt != (deleting ? events : 0u)))
    return 3;
  std::cout << observerMask << ' ' << (timerReleaseAt != 0) << ' '
            << actualReleases << ' ' << (timers.at(0) == otherTimer) << '\n';
  return 0;
}
} // namespace

int main(int argc, char **argv) {
  const std::string_view mode = argc == 2 ? argv[1] : "";
  if (mode == "cast") {
    int type;
    PanMeterControl meter(1);
    while (std::cin >> type) {
      Control &base = meter;
      std::cout << (base.castTo(type) == &meter) << '\n';
    }
    return std::cin.eof() ? 0 : 5;
  }
  if (mode == "c1" || mode == "c2") {
    struct DerivedPan : PanMeterControl {
      explicit DerivedPan(int tag) : PanMeterControl(tag) {}
    };
    auto observe = [](PanMeterControl &meter) {
      using Access = presonus::panel::MeterLevelControlAccess;
      std::cout << ControlAccess::tag(meter) << ' '
                << ControlAccess::lastLevel(meter) << ' '
                << (meter.getParameter() != nullptr) << ' '
                << (meter.getAltParameter() != nullptr) << ' '
                << (meter.getTertiaryParameter() != nullptr) << ' '
                << (ControlAccess::io(meter) != nullptr) << ' '
                << MeterControlAccess::direction(meter) << ' '
                << (MeterControlAccess::overrideCount(meter) != nullptr) << ' '
                << Access::parameterMode(meter) << ' '
                << Access::clipActive(meter) << ' '
                << (meter.castTo(0x50616e43) == &meter) << '\n';
    };
    int tag;
    while (std::cin >> tag) {
      if (mode == "c1") {
        PanMeterControl meter(tag);
        observe(meter);
      } else {
        DerivedPan meter(tag);
        observe(meter);
      }
    }
    return std::cin.eof() ? 0 : 5;
  }
  if (mode != "provider" && mode != "complete" && mode != "deleting")
    return 4;
  int tag;
  unsigned mask;
  bool timer;
  while (std::cin >> tag >> mask >> timer) {
    if (const auto error =
            exercise(tag, mask, timer, mode == "provider", mode == "deleting"))
      return error;
  }
  return std::cin.eof() ? 0 : 5;
}
