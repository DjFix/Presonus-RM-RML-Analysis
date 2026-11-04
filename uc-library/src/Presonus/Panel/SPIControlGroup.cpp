#include "presonus/panel/SPIControlGroup.hpp"
#include "presonus/panel/control.hpp"
#include <algorithm>
#include <linux/spi/spidev.h>
#include <stdexcept>
#include <sys/ioctl.h>

namespace presonus::spi_port {
void LinuxTransfer::submit(int descriptor, std::uint32_t request,
                           const std::uint8_t *transmit, std::uint8_t *receive,
                           int length) {
  spi_ioc_transfer message{};
  message.tx_buf = reinterpret_cast<std::uintptr_t>(transmit);
  message.rx_buf = reinterpret_cast<std::uintptr_t>(receive);
  message.len = static_cast<decltype(message.len)>(length);
  // Device return status was ignored by the observed idle path. This provider
  // deliberately retains that behavior; it never opens or configures a device.
  ::ioctl(descriptor, static_cast<unsigned long>(request), &message);
}
} // namespace presonus::spi_port
namespace {
presonus::spi_port::LinuxTransfer linuxTransfer;
}
namespace Presonus::Panel {
SPIControlGroup::SPIControlGroup(int groupId, int groupArgument, int byteCount)
    : ControlGroup(groupId, groupArgument), byteCount(byteCount),
      descriptor(-1), transfer(&linuxTransfer), dirty(true) {}
SPIControlGroup::SPIControlGroup(
    const Core::ConstVector<std::uint32_t> &controls, int byteCount,
    int descriptor, presonus::spi_port::Transfer &transfer)
    : ControlGroup(0, 0), borrowedWords(&controls), byteCount(byteCount),
      descriptor(descriptor), transfer(&transfer) {
  if (byteCount > 8)
    throw std::invalid_argument(
        "SPI idle payload exceeds bounded 64-bit domain");
}
void SPIControlGroup::onIdle() {
  if (!dirty || descriptor < 0)
    return;
  dirty = false;
  std::uint64_t payload = 0;
  if (byteCount > 0) {
    const int controlCount = borrowedWords ? borrowedWords->count() : count();
    // Avoid signed multiplication overflow and undefined shifts outside the
    // previously bounded portable 64-bit payload domain.
    const int limit = byteCount >= 8 ? 64 : byteCount * 8;
    for (int i = 0; i < std::min(controlCount, limit); ++i) {
      const auto value =
          borrowedWords
              ? borrowedWords->at(i)
              : static_cast<std::uint32_t>(
                    presonus::panel::ControlAccess::lastLevel(*at(i)));
      if (value != 0)
        payload |= std::uint64_t{1} << i;
    }
  }
  if (byteCount < 2 || byteCount > 5)
    return;
  for (int i = 0; i < byteCount; ++i) {
    transmit[i] = static_cast<std::uint8_t>(payload >> (i * 8));
    receive[i] = 0;
  }
  transfer->submit(descriptor, 0x40206b00u, transmit.data(), receive.data(),
                   byteCount);
}
} // namespace Presonus::Panel
