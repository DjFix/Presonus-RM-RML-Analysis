#include "presonus/pcm4104/Pcm4104Spi.hpp"

#include "core/system/coredebug.h"

#include <cerrno>
#include <cmath>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <unistd.h>

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

Pcm4104Spi::Pcm4104Spi(const char *path) { open(path); }

Pcm4104Spi::Pcm4104Spi(BorrowedDescriptor, int descriptor)
    : descriptor_(descriptor) {}

Pcm4104Spi::~Pcm4104Spi() {
  if (ownsDescriptor_ && descriptor_ != 0)
    ::close(descriptor_);
}

Pcm4104Spi Pcm4104Spi::withBorrowedSpiDescriptor(int descriptor) {
  return Pcm4104Spi(BorrowedDescriptor{}, descriptor);
}

bool Pcm4104Spi::open(const char *path) {
  // The original replaces the descriptor even when setup fails.
  descriptor_ = ::open(path, O_RDWR);
  ownsDescriptor_ = descriptor_ > 0;
  if (descriptor_ < 0) {
    Core::DebugPrintf("SPI: Failed to open PCM4104 SPI port\n");
  } else {
    std::uint8_t mode = 0;
    if (::ioctl(descriptor_, SPI_IOC_RD_MODE, &mode) < 0) {
      Core::DebugPrintf("SPI: error reading mode %d\n", static_cast<int>(mode));
    } else {
      mode &= static_cast<std::uint8_t>(~(SPI_CPOL | SPI_CPHA));
      if (::ioctl(descriptor_, SPI_IOC_WR_MODE, &mode) >= 0)
        return configureDefaults();
      Core::DebugPrintf("SPI error writing mode %d\n", static_cast<int>(mode));
    }
  }
  descriptor_ = 0;
  ownsDescriptor_ = false;
  return false;
}

bool Pcm4104Spi::configureDefaults() {
  for (int index = 1; index <= 7; ++index)
    writeRegister(index, index <= 4 ? 0xff : 0);
  return true;
}

bool Pcm4104Spi::muteChannel(int channel, bool muted) {
  if (channel < 0 || channel >= 4)
    return false;
  auto &cached = attenuationCache_[channel];
  return readRegister(channel, &cached) &&
         setAttenuationValue(channel, muted ? 0 : cached);
}

bool Pcm4104Spi::attenuateChannel(int channel, float gain) {
  if (channel > 3)
    return false;
  const float value = std::log10(gain / 1.995f) * 40.0f + 255.0f;
  unsigned char attenuation = 0;
  if (value >= 0.0f) {
    attenuation =
        std::isinf(value)
            ? 0xff
            : static_cast<unsigned char>(static_cast<unsigned>(value));
  }
  return setAttenuationValue(channel, attenuation);
}

bool Pcm4104Spi::setAttenuationValue(int channel, unsigned char value) {
  const auto reg = lookupChannelAttenuationRegister(channel);
  return writeRegister(static_cast<unsigned char>(reg), value) &&
         writeRegister(static_cast<unsigned char>(reg + 1), value);
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
