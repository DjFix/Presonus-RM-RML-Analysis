#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/spi_packets.hpp"

namespace Presonus::NOAA {
void TCardHandler::release() {
  TCardSPI::instance().release();
  state_.stopRequested.store(true, std::memory_order_release);
  // Actual pinned CCL source provider; its Linux implementation cancels the
  // live thread. It does not join or destroy the handler, card or SPI service.
  Core::Threads::Thread::terminate();
}
} // namespace Presonus::NOAA
