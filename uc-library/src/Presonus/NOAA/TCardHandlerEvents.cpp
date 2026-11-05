#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include "presonus/noaa/router.hpp"
#include "presonus/noaa/spi_packets.hpp"
#include <stdexcept>
namespace Presonus::NOAA {
int TCardHandler::threadEntry() {
  if (state_.stopRequested.load(std::memory_order_acquire))
    return 0;
  // Original shared static identity and signed64 ordering. Caller serializes
  // threadEntry across instances; this is not a per-instance deadline.
  static std::int64_t s_LastIdleTicks = 0;
  std::uint32_t counter = 0;
  do {
    if (state_.eventQueue)
      state_.eventQueue->consumeOne(*this, state_);
    // Pinned Linux CCL clock reports signed nanoseconds. Preserve the exact
    // native integer division, avoiding the provider's floating ms conversion.
    auto now =
        static_cast<std::int64_t>(Core::SystemClock::getTime() / 1000000);
    if (now > s_LastIdleTicks) {
      if (!state_.router)
        throw std::invalid_argument("Handler thread requires a router");
      // Modulo addition matches the observed two-word ARM carry even at the
      // extreme signed boundary; implementation targets Linux two's complement.
      s_LastIdleTicks =
          static_cast<std::int64_t>(static_cast<std::uint64_t>(now) + 20u);
      state_.router->idle();
    }
    ++counter;
    TCardSPI::instance().onIdle((counter & 63u) == 0);
    Core::Threads::CurrentThread::sleep(2);
  } while (!state_.stopRequested.load(std::memory_order_acquire));
  return 0;
}
void TCardHandler::purgeEvents() {
  auto *pending = state_.pendingEventCount;
  if (!pending)
    throw std::invalid_argument(
        "purgeEvents requires a borrowed pending count");
  while (pending->load(std::memory_order_acquire) != 0)
    Core::Threads::CurrentThread::sleep(10);
}
} // namespace Presonus::NOAA
