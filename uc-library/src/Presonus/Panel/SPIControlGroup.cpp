#include "presonus/panel/SPIControlGroup.hpp"
#include <algorithm>
#include <stdexcept>
namespace Presonus::Panel {
SPIControlGroup::SPIControlGroup(
    const Core::ConstVector<std::uint32_t> &controls, int byteCount,
    int descriptor, presonus::spi_port::Transfer &transfer)
    : controls(controls), byteCount(byteCount), descriptor(descriptor),
      transfer(transfer) {
  if (byteCount > 8)
    throw std::invalid_argument(
        "SPI idle payload exceeds bounded 64-bit domain");
}
void SPIControlGroup::onIdle() {
  if (!dirty || descriptor < 0)
    return;
  dirty = false;
  std::uint64_t payload = 0;
  if (byteCount > 0)
    for (int i = 0; i < std::min(controls.count(), byteCount * 8); ++i)
      if (controls.at(i) != 0)
        payload |= std::uint64_t{1} << i;
  // Observed callee behavior, kept as a source-port adaptation. No competing
  // original bitBang declaration or original layout is introduced here.
  if (byteCount < 2 || byteCount > 5)
    return;
  for (int i = 0; i < byteCount; ++i) {
    transmit[i] = static_cast<std::uint8_t>(payload >> (i * 8));
    receive[i] = 0;
  }
  transfer.submit(descriptor, 0x40206b00u, transmit.data(), receive.data(),
                  byteCount);
}
} // namespace Presonus::Panel
