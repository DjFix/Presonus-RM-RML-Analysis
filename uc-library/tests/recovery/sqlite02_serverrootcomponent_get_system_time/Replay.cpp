#include "presonus/uc/ServerRootComponent.hpp"

#include "core/system/coretime.h"

#include <ctime>
#include <iostream>
#include <optional>

namespace {
std::optional<Core::abs_time> injectedNanoseconds;
constexpr Core::abs_time kNanosecondsPerSecond = 1000000000;
} // namespace

extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *out) {
  if (clock == CLOCK_MONOTONIC && injectedNanoseconds) {
    out->tv_sec = *injectedNanoseconds / kNanosecondsPerSecond;
    out->tv_nsec = *injectedNanoseconds % kNanosecondsPerSecond;
    return 0;
  }
  return __real_clock_gettime(clock, out);
}

int main() {
  const Presonus::UC::ServerRootComponent root("local root");
  Core::abs_time tick;
  while (std::cin >> tick) {
    injectedNanoseconds = tick;
    std::cout << root.getSystemTime() << ' '
              << Core::SystemClock::getMilliseconds() << '\n';
    injectedNanoseconds.reset();
  }
  // Both methods use the real monotonic clock with injection disabled.
  const auto lower = Core::SystemClock::getTime() / 1000000;
  const auto current = root.getSystemTime();
  const auto provider = Core::SystemClock::getMilliseconds();
  const auto upper = Core::SystemClock::getTime() / 1000000;
  return lower <= current && current <= upper && lower - 1 <= provider &&
                 provider <= upper + 1
             ? 0
             : 1;
}
