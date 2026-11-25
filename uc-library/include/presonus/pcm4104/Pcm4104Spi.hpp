#pragma once

#include <cstdint>

namespace Presonus::PCM4104 {
// Portable source port. Original class layout and return declarations are
// unresolved.
class Pcm4104Spi {
public:
  // Independent portable entry for an already configured Linux SPI descriptor.
  // The caller retains ownership. Zero leaves this receiver disconnected.
  static Pcm4104Spi withBorrowedSpiDescriptor(int descriptor);

  bool readRegister(int registerIndex, unsigned char *value);
  bool writeRegister(int registerIndex, unsigned char value);
  std::uint32_t lookupChannelAttenuationRegister(int channel);

private:
  int descriptor_ = 0;
  [[maybe_unused]] std::uint8_t attenuationCache_[4] = {0xff, 0xff, 0xff, 0xff};
};
} // namespace Presonus::PCM4104
