#include "core/public/corebuffer.h"
#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/dice/programmer_services.hpp"
#include <cstring>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>

namespace presonus::dice {
std::int32_t
LinuxProgrammerTransport::transfer(std::int32_t descriptor,
                                   const ProgrammerTransfer &transfer) {
  const std::uint32_t total = transfer.transmitLength + transfer.receiveLength;
  // Explicit source-port bounds: arbitrary invalid pointers/count overflow and
  // oversized transfers are outside the retained original witness domain.
  if (total < transfer.transmitLength || total > 65536 ||
      (transfer.transmitLength != 0 && transfer.transmit == nullptr) ||
      (total != 0 && transfer.receive == nullptr))
    return -1;
  Core::IO::Buffer staged;
  if (!staged.resize(total))
    return -1;
  if (total != 0) {
    std::memset(staged.getAddress(), 0, total);
    if (transfer.transmitLength != 0)
      std::memcpy(staged.getAddress(), transfer.transmit,
                  transfer.transmitLength);
  }
  spi_ioc_transfer request{};
  request.tx_buf = reinterpret_cast<std::uintptr_t>(staged.getAddress());
  request.rx_buf = reinterpret_cast<std::uintptr_t>(transfer.receive);
  request.len = total;
  request.speed_hz = 1000000;
  request.bits_per_word = 8;
  return ::ioctl(descriptor, SPI_IOC_MESSAGE(1), &request);
}

std::int32_t
CclProgrammerServices::transfer(std::int32_t descriptor,
                                const ProgrammerTransfer &transfer) {
  return transport_.transfer(descriptor, transfer);
}
std::int64_t CclProgrammerServices::clockRawTicks() {
  return Core::SystemClock::getTime();
}
void CclProgrammerServices::sleepMilliseconds(std::uint32_t milliseconds) {
  Core::Threads::CurrentThread::sleep(milliseconds);
}
} // namespace presonus::dice
