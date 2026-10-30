#include "core/system/corethread.h"
#include "presonus/dice/manager_services.hpp"
#include "presonus/dice/packet_services.hpp"

namespace presonus::dice {
std::int64_t CclManagerServices::clockRawTicks() {
  return packetClockRawTicks();
}
void CclManagerServices::sleepMilliseconds(std::uint32_t milliseconds) {
  Core::Threads::CurrentThread::sleep(milliseconds);
}
void CclManagerServices::terminateThread() { thread_.terminate(); }
} // namespace presonus::dice
