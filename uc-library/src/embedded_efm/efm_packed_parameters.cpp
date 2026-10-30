#include "presonus/embedded_efm/efm_packed_parameters.hpp"
#include "presonus/embedded_efm/efm_parameter_fields.hpp"
#include <algorithm>

namespace presonus::analysis::efm_fader_packed_parameters {
namespace {
constexpr std::size_t packetOffset = 0x144;
constexpr std::size_t contextOffset = 0x1d8;
std::uint32_t loadWord(const std::uint8_t *source) {
  return std::uint32_t(source[0]) | (std::uint32_t(source[1]) << 8) |
         (std::uint32_t(source[2]) << 16) | (std::uint32_t(source[3]) << 24);
}
void storeWord(std::uint8_t *destination, std::uint32_t value) {
  for (unsigned i = 0; i < 4; ++i)
    destination[i] = static_cast<std::uint8_t>(value >> (i * 8));
}
} // namespace

bool applyPackedParameterPacket(std::uint8_t *ram, std::size_t capacity) {
  if (!ram || capacity <= 0x1d4)
    return false;
  auto *packet = ram + packetOffset;
  const unsigned command = packet[1] & 0x7f;
  if (command != 0x20 && command != 0x22 && command != 0x28)
    return false;
  const unsigned destination = packet[0] >> 4;
  if (destination != ram[0x1d4] && destination != 15)
    return true;
  const bool read = (packet[1] & 0x80) != 0;
  const unsigned selector = packet[0] & 15;
  const auto first = static_cast<std::uint8_t>(selector == 15 ? 0 : selector);
  const auto last =
      static_cast<std::uint8_t>(selector == 15 ? 4 : selector + 1);
  const std::size_t field = command == 0x20   ? 0x38
                            : command == 0x28 ? 0x30
                                              : 0x100;
  const std::size_t stride = command == 0x22 ? 40 : 64;
  const std::size_t fieldSize = command != 0x22 ? 8 : read ? 1 : 4;
  const std::size_t stateEnd =
      contextOffset + field + std::size_t(last - 1) * stride + fieldSize;
  const std::size_t packetEnd = packetOffset + 3 + last;
  // Portable bounds are checked before mutation; original code has no guards.
  if (capacity < stateEnd || capacity < packetEnd ||
      (!read && command == 0x20 && capacity < 0x3c8) ||
      (!read && command == 0x22 && capacity < 0x3c9))
    return false;
  auto *context = ram + contextOffset;
  using namespace presonus::analysis::efm_fader_parameters;
  if (command == 0x22) {
    if (read)
      return transferStrided(
          Transfer::ReadByte, packet, capacity - packetOffset, context + 0x100,
          capacity - contextOffset - 0x100, 40, 1, first, last);
    for (unsigned i = first; i < last; ++i) {
      const auto value = packet[3 + i];
      if (value != 0 && ram[0x3c8] == 0) {
        context[0x101 + i * 40] = value;
        context[0x103 + i * 40] |= 0x80;
      }
    }
    return true;
  }
  if (read) {
    for (unsigned i = first; i < last; ++i) {
      const auto *source = context + field + i * 64;
      packet[3 + i] = static_cast<std::uint8_t>((loadWord(source) << 4) |
                                                (loadWord(source + 4) & 15));
    }
    packet[2] = static_cast<std::uint8_t>(last - first);
    packet[1] &= 0x7f;
    return true;
  }
  if (!transferStrided(Transfer::WriteZeroExtendedWord, packet,
                       capacity - packetOffset, context + field + 4,
                       capacity - contextOffset - field - 4, 64, 1, first,
                       last))
    return false;
  for (unsigned i = first; i < last; ++i) {
    auto *destinationWord = context + field + i * 64;
    const auto value = loadWord(destinationWord + 4);
    storeWord(destinationWord, (value >> 4) & 15);
    storeWord(destinationWord + 4, value & 15);
  }
  if (command == 0x20) {
    ram[0x1c8] = 1;
    std::fill_n(ram + 0x3c0, 8, 0);
    std::fill_n(ram + 0x3ac, 8, 0);
    ram[0xe2] = 100;
    ram[0xe3] = 0;
  }
  return true;
}
} // namespace presonus::analysis::efm_fader_packed_parameters
