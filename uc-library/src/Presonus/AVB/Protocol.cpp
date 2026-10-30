#include "presonus/avb/protocol.hpp"
#include "presonus/dice/sysex.hpp"

#include <cstddef>
#include <cstdint>
#include <cstring>

static_assert(sizeof(int) == 4);
static_assert(sizeof(unsigned long long) == 8);

namespace Presonus::AVB {
bool AvbManagerBase::accepts(const DICE::SysexPacket &packet) {
  if (packet.length <= 1)
    return false;
  const auto command = packet.bytes[1];
  if (command < 0x23 || command > 0x2f)
    return false;
  return (0x1dbfU & (1U << (command - 0x23U))) != 0;
}

int AvbManagerBase::unpackAvbSpiMsg(unsigned char *destination,
                                    const unsigned char *source, int length) {
  if (length > 64)
    return -1;
  // The original subtract wraps at32bits, then divides signed with truncation.
  const std::uint32_t deltaWord = static_cast<std::uint32_t>(length) - 3U;
  std::int32_t delta;
  std::memcpy(&delta, &deltaWord, sizeof delta);
  const auto count = delta / 2;
  destination[0] = source[0];
  destination[1] = source[1];
  for (std::int32_t index = 0; index < count; ++index) {
    const auto high = source[2 + 2 * index];
    const auto low = source[3 + 2 * index];
    destination[2 + index] = static_cast<unsigned char>((high << 4) | low);
  }
  destination[static_cast<std::ptrdiff_t>(count) + 2] =
      source[static_cast<std::ptrdiff_t>(length) - 1];
  return 0;
}

unsigned long long AvbManagerBase::reverseEndian(unsigned long long value) {
  unsigned long long result = 0;
  for (unsigned int index = 0; index < 8; ++index) {
    result = (result << 8) | (value & 0xffU);
    value >>= 8;
  }
  return result;
}

void AvbManagerBase::char2Nibble(const unsigned char *source,
                                 unsigned char *destination, int length) {
  for (int index = 0; index < length; ++index) {
    const auto value = source[index];
    destination[0] = static_cast<unsigned char>(value >> 4);
    destination[1] = static_cast<unsigned char>(value & 0xfU);
    destination += 2;
  }
}

void AvbManagerBase::nibble2Char(const unsigned char *source,
                                 unsigned char *destination, int length) {
  for (int index = 0; index < length; ++index) {
    const auto high = source[0];
    const auto low = source[1];
    source += 2;
    destination[index] = static_cast<unsigned char>((high << 4) | low);
  }
}
} // namespace Presonus::AVB
