#pragma once

#include <cstdint>

namespace Presonus::PCM4104 {
// Portable source port. Original class layout and return declarations are
// unresolved.
class Pcm4104Spi {
public:
  Pcm4104Spi() = default;
  explicit Pcm4104Spi(const char *path);
  ~Pcm4104Spi();

  Pcm4104Spi(const Pcm4104Spi &) = delete;
  Pcm4104Spi &operator=(const Pcm4104Spi &) = delete;

  bool open(const char *path);
  bool configureDefaults();
  bool muteChannel(int channel, bool muted);
  bool attenuateChannel(int channel, float gain);
  bool setAttenuationValue(int channel, unsigned char value);

  // Independent portable entry for an already configured Linux SPI descriptor.
  // The caller retains ownership. Zero leaves this receiver disconnected.
  static Pcm4104Spi withBorrowedSpiDescriptor(int descriptor);

  bool readRegister(int registerIndex, unsigned char *value);
  bool writeRegister(int registerIndex, unsigned char value);
  std::uint32_t lookupChannelAttenuationRegister(int channel);

private:
  struct BorrowedDescriptor {};
  Pcm4104Spi(BorrowedDescriptor, int descriptor);

  int descriptor_ = 0;
  std::uint8_t attenuationCache_[4] = {0xff, 0xff, 0xff, 0xff};
  bool ownsDescriptor_ = false;
};
} // namespace Presonus::PCM4104
