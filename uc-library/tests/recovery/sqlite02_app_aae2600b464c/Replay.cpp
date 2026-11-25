#include "presonus/mixer/NetworkSelectComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {
using namespace Presonus;
using namespace Core::Portable;
using UC::MessageAttributes;

struct Services final : presonus::network_select::NetworkServices {
  int calls = 0;
  void serverNotify(const MessageAttributes &) override { ++calls; }
  void scan(bool) override { ++calls; }
  void idle() override { ++calls; }
  void join(const char *, const char *) override { ++calls; }
  void updateList(ListParam *, ListParam *, ListParam *, bool) override {
    ++calls;
  }
  void suspendAdaptors(bool) override { ++calls; }
  void configureInterface(const char *) override { ++calls; }
  const char *managerName(const WIFIManager &) const override { std::abort(); }
  const char *managerSSID(const WIFIManager &) const override { std::abort(); }
  const char *managerIP(const WIFIManager &, int) override { std::abort(); }
  const void *find(const char *) override { std::abort(); }
  bool hasFlag(const void *, const char *) override { std::abort(); }
  const char *signalText(const void *) const override { std::abort(); }
};

DelayTimer *scan;
DelayTimer *configuration;
int calls;
} // namespace

extern "C" void __real__ZN8Presonus10DelayTimer11beginActionEf(DelayTimer *,
                                                               float);
extern "C" void
__wrap__ZN8Presonus10DelayTimer11beginActionEf(DelayTimer *timer, float value) {
  if (timer != scan && timer != configuration)
    std::abort();
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  std::cout << (timer == scan ? 0 : 1) << ' ' << bits << '\n';
  ++calls;
  __real__ZN8Presonus10DelayTimer11beginActionEf(timer, value);
}

int main() {
  Services services;
  Presonus::Mixer::NetworkSelectComponent first(services);
  Presonus::Mixer::NetworkSelectComponent second(services);
  try {
    first.initialize();
    return 1;
  } catch (const std::logic_error &) {
  }
  DelayTimer firstScan(0.25f), firstConfig(0.5f);
  DelayTimer secondScan(0.75f), secondConfig(1.0f);
  first.configureTimers(firstScan, firstConfig);
  second.configureTimers(secondScan, secondConfig);

  const auto exercise = [](auto &component, auto &scanTimer,
                           auto &configTimer) {
    scan = &scanTimer;
    configuration = &configTimer;
    using presonus::timing::DelayTimerAccess;
    const auto scanBefore = DelayTimerAccess::get(scanTimer);
    const auto configBefore = DelayTimerAccess::get(configTimer);
    component.initialize();
    const auto scanAfter = DelayTimerAccess::get(scanTimer);
    const auto configAfter = DelayTimerAccess::get(configTimer);
    return scanAfter.executing && configAfter.executing &&
           scanAfter.elapsed == 0 && configAfter.elapsed == 0 &&
           scanBefore.duration == scanAfter.duration &&
           configBefore.duration == configAfter.duration &&
           scanBefore.reciprocal == scanAfter.reciprocal &&
           configBefore.reciprocal == configAfter.reciprocal;
  };
  return exercise(first, firstScan, firstConfig) && !secondScan.isExecuting() &&
                 !secondConfig.isExecuting() &&
                 exercise(second, secondScan, secondConfig) && calls == 4 &&
                 services.calls == 0
             ? 0
             : 1;
}
