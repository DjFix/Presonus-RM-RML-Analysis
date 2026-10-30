#include "presonus/noaa/programmer.hpp"
#include <cstring>
#include <unistd.h>

namespace {
// Independent common helper for the two original inlined XOR loops. The
// original method name says CRC, but observed behavior is bytewise XOR only.
std::uint32_t xorBytes(const unsigned char *data, int length) {
  std::uint32_t value = 0;
  for (int i = 0; i < length; ++i)
    value ^= data[i];
  return value;
}
std::int32_t armWordResult(ssize_t value) {
  const auto bits = static_cast<std::uint32_t>(value);
  std::int32_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
class PosixTransport final : public presonus::noaa::ProgrammerTransport {
public:
  std::int32_t write(std::int32_t descriptor, const unsigned char *data,
                     std::uint32_t count) override {
    return armWordResult(::write(descriptor, data, count));
  }
  std::int32_t close(std::int32_t descriptor) override {
    return ::close(descriptor);
  }
};
} // namespace

namespace presonus::noaa {
ProgrammerTransport &posixProgrammerTransport() {
  static PosixTransport transport;
  return transport;
}
} // namespace presonus::noaa

namespace Presonus::NOAA {
std::uint32_t TCardProgrammer::calcCRC(const unsigned char *data, int length) {
  return xorBytes(data, length);
}
std::int32_t TCardProgrammer::write(const unsigned char *data, int length) {
  // Original ARM32 size_t receives the unchanged 32-bit count word. Do not
  // sign-extend a negative int into a native 64-bit size_t or silently cap it.
  return transport_->write(state_.descriptor, data,
                           static_cast<std::uint32_t>(length));
}
std::int32_t TCardProgrammer::writeChar(unsigned char value) {
  return transport_->write(state_.descriptor, &value, 1);
}
std::int32_t TCardProgrammer::sendPacket(const unsigned char *data,
                                         int length) {
  const auto checksum = xorBytes(data, length);
  // The original ignores partial/failed payload writes and returns only the
  // checksum-byte write result. Preserve that behavior; do not invent retries.
  transport_->write(state_.descriptor, data,
                    static_cast<std::uint32_t>(length));
  return writeChar(static_cast<unsigned char>(checksum));
}
std::int32_t TCardProgrammer::sendAddress(unsigned int address) {
  const unsigned char bytes[]{static_cast<unsigned char>(address >> 24),
                              static_cast<unsigned char>(address >> 16),
                              static_cast<unsigned char>(address >> 8),
                              static_cast<unsigned char>(address)};
  return sendPacket(bytes, 4);
}
std::int32_t TCardProgrammer::close() {
  const auto result =
      state_.descriptor == -1 ? -1 : transport_->close(state_.descriptor);
  state_.descriptor = -1;
  return result;
}
} // namespace Presonus::NOAA
