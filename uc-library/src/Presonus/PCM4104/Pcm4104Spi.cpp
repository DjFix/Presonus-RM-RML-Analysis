#include "presonus/pcm4104/Pcm4104Spi.hpp"

#include "core/system/coredebug.h"

#include <cerrno>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>

namespace Presonus::PCM4104 {
namespace {
bool transferRegister(int descriptor, const unsigned char (&tx)[2],
                      unsigned char (&rx)[2]) {
  spi_ioc_transfer transfer{};
  transfer.tx_buf = reinterpret_cast<std::uintptr_t>(tx);
  transfer.rx_buf = reinterpret_cast<std::uintptr_t>(rx);
  transfer.len = sizeof(tx);
  transfer.speed_hz = 1000000;
  transfer.bits_per_word = 8;
  if (::ioctl(descriptor, SPI_IOC_MESSAGE(1), &transfer) >= 0)
    return true;
  const int transferError = errno;
  Core::DebugPrintf("SPI error on transfer: %d\n", transferError);
  return false;
}
} // namespace

Pcm4104Spi Pcm4104Spi::withBorrowedSpiDescriptor(int descriptor) {
  Pcm4104Spi spi;
  spi.descriptor_ = descriptor;
  return spi;
}

bool Pcm4104Spi::readRegister(int registerIndex, unsigned char *value) {
  if (descriptor_ == 0)
    return false;
  const unsigned char tx[] = {static_cast<unsigned char>(registerIndex | 0xa0),
                              0};
  unsigned char rx[2]{};
  if (!transferRegister(descriptor_, tx, rx))
    return false;
  *value = rx[1];
  return true;
}

bool Pcm4104Spi::writeRegister(int registerIndex, unsigned char value) {
  if (descriptor_ == 0)
    return false;
  const unsigned char tx[] = {static_cast<unsigned char>(registerIndex | 0x20),
                              value};
  unsigned char rx[2]{};
  return transferRegister(descriptor_, tx, rx);
}

std::uint32_t Pcm4104Spi::lookupChannelAttenuationRegister(int channel) {
  // ARM ADD wraps in 32 bits, including channel == INT_MAX.
  return static_cast<std::uint32_t>(channel) + std::uint32_t{1};
}
} // namespace Presonus::PCM4104
