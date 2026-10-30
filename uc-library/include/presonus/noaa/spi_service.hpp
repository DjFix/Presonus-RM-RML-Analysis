#pragma once
#include <cstdint>

namespace presonus::noaa {
// Independent logical transfer boundary; not the original/kernel pointer ABI.
struct SpiTransfer {
  const unsigned char *tx;
  unsigned char *rx;
  std::uint32_t length;
  std::uint32_t speed = 20000000;
  std::uint16_t delay = 0;
  unsigned char bits = 8;
  unsigned char csChange = 0;
};
class SpiServiceIO {
public:
  virtual ~SpiServiceIO() = default;
  virtual int open(const char *path, int flags) = 0;
  virtual int maxSpeed(int descriptor, std::uint32_t speed) = 0;
  virtual int transfer(int descriptor, const SpiTransfer &transfer) = 0;
  virtual int close(int descriptor) = 0;
  virtual int errorNumber() = 0;
  virtual std::int64_t rawTicks() = 0;
  virtual void diagnostic(bool standardOutput, const char *format, int value,
                          bool hasArgument) = 0;
};
SpiServiceIO &spiServiceConstructionIO();
// Independent thread-local selection; retained service must outlive its owner.
SpiServiceIO *setSpiServiceConstructionIO(SpiServiceIO *io);
struct SpiServiceAccess;
} // namespace presonus::noaa
