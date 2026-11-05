#include "core/system/corethread.h"
#include "presonus/noaa/card_handler.hpp"
#include <stdexcept>
namespace Presonus::NOAA {
void TCardHandler::purgeEvents() {
  auto *pending = state_.pendingEventCount;
  if (!pending)
    throw std::invalid_argument(
        "purgeEvents requires a borrowed pending count");
  while (pending->load(std::memory_order_acquire) != 0)
    Core::Threads::CurrentThread::sleep(10);
}
} // namespace Presonus::NOAA
