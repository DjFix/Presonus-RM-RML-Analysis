#pragma once
#include <cstdint>

namespace presonus::dice {
// Independent source-port transport DTO, not an original SPI ABI structure.
// receiveLength counts payload bytes only. The receive pointer MUST provide
// writable capacity >= transmitLength + receiveLength, including command bytes.
// transmit needs transmitLength initialized bytes. Linux transport stages the
// remaining transmit tail with zeros; original inactive bytes are unverified.
struct ProgrammerTransfer {
  const unsigned char *transmit;
  std::uint32_t transmitLength;
  unsigned char *receive;
  std::uint32_t receiveLength;
};
class ProgrammerTransport {
public:
  virtual ~ProgrammerTransport() = default;
  virtual std::int32_t transfer(std::int32_t descriptor,
                                const ProgrammerTransfer &transfer) = 0;
};
class ProgrammerServices : public ProgrammerTransport {
public:
  virtual std::int64_t clockRawTicks() = 0;
  virtual void sleepMilliseconds(std::uint32_t milliseconds) = 0;
};
// Source-based Linux SPI transport. Tests intercept ioctl; never use it to
// perform physical programming/erase/updates during reconstruction.
class LinuxProgrammerTransport final : public ProgrammerTransport {
public:
  std::int32_t transfer(std::int32_t descriptor,
                        const ProgrammerTransfer &transfer) override;
};
// Real pinned CCL source supplies clocks/sleep; SPI remains an explicit app
// transport boundary. No legacy Core class or firmware Core body is defined.
class CclProgrammerServices final : public ProgrammerServices {
public:
  explicit CclProgrammerServices(ProgrammerTransport &transport)
      : transport_(transport) {}
  std::int32_t transfer(std::int32_t descriptor,
                        const ProgrammerTransfer &transfer) override;
  std::int64_t clockRawTicks() override;
  void sleepMilliseconds(std::uint32_t milliseconds) override;

private:
  ProgrammerTransport &transport_;
};
} // namespace presonus::dice
