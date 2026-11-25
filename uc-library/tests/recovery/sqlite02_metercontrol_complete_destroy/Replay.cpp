#include "presonus/surface_panel/MeterControl.hpp"

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
using Presonus::Panel::MeterControl;
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
[[gnu::noipa]] void destroyThroughBase(Control *base) { delete base; }

int exercise(int tag, unsigned mask, bool trackedTimer, bool provider,
             bool deleting) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.maxValue = 1.f;
  NumericParam primary(info), alternate(info), tertiary(info);
  trackedParameters[0] = &primary;
  trackedParameters[1] = &alternate;
  trackedParameters[2] = &tertiary;
  alignas(MeterControl) unsigned char buffer[sizeof(MeterControl)];
  int borrowedCount = 17;
  auto *meter = provider   ? nullptr
                : deleting ? new MeterControl(tag)
                           : new (buffer) MeterControl(tag);
  Control *control =
      meter ? static_cast<Control *>(meter) : new (buffer) Control(tag);
  if (meter)
    MeterControlAccess::setState(*meter, &borrowedCount, 1);
  Control other(999);
  other.startTimer(1.f, 9);
  auto &timers = ControlAccess::timers();
  if (timers.count() != 1)
    return 1;
  const auto *otherTimer = timers.at(0);
  if (mask & 1)
    control->setParameter(&primary, 0);
  if (mask & 2)
    control->setAltParameter(&alternate);
  if (mask & 4)
    control->setTertiaryParameter(&tertiary);
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
    control->Control::~Control();
  else if (deleting)
    destroyThroughBase(control);
  else
    meter->MeterControl::~MeterControl();
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
