#include "core/system/coredebug.h"
#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/dice/response_services.hpp"
#include <cstring>

#if !defined(__linux__)
#error "This raw-nanosecond legacy DICE adapter is Linux-only."
#endif

namespace presonus::dice {
std::int64_t CclResponseServices::clockRawTicks() {
  // POSIX source returns CLOCK_MONOTONIC nanoseconds. The app divides by1e6.
  return Core::SystemClock::getTime();
}
void CclResponseServices::pumpIdle(bool force) { pump_.onIdle(force); }
void CclResponseServices::sleepMilliseconds(std::uint32_t milliseconds) {
  Core::Threads::CurrentThread::sleep(milliseconds);
}
void CclResponseServices::timeoutNotice(bool responseSet,
                                        std::uint32_t response,
                                        std::uint32_t timeoutLowWord) {
  if (!responseSet) {
    Core::DebugPrintf("ack timeout\n");
    return;
  }
  int responseValue, timeoutValue;
  static_assert(sizeof(int) == sizeof(std::uint32_t));
  std::memcpy(&responseValue, &response, sizeof responseValue);
  std::memcpy(&timeoutValue, &timeoutLowWord, sizeof timeoutValue);
  Core::DebugPrintf("waitResponseSet timeout:%d %d\n", responseValue,
                    timeoutValue);
}
} // namespace presonus::dice
