#include "presonus/embedded_efm/efm_parameter_fields.hpp"

namespace presonus::analysis::efm_fader_parameters {
bool transferStrided(Transfer operation, std::uint8_t *packet,
                     std::size_t packetCapacity, std::uint8_t *state,
                     std::size_t stateCapacity, std::uint32_t stateStride,
                     std::uint32_t packetStride, std::uint8_t first,
                     std::uint8_t last) {
  if (!packet || !state || packetCapacity < 3)
    return false;
  const bool read =
      operation == Transfer::ReadByte || operation == Transfer::ReadWordLowByte;
  const bool word = operation == Transfer::ReadWordLowByte ||
                    operation == Transfer::WriteZeroExtendedWord;
  if (word)
    stateStride &= ~std::uint32_t(3);
  // Validate the entire portable buffer domain before any mutation.
  if (first < last) {
    const std::uint64_t index = last - 1;
    const std::uint64_t packetEnd = 3 + index * packetStride + 1;
    const std::uint64_t stateEnd =
        index * stateStride +
        (operation == Transfer::WriteZeroExtendedWord ? 4 : 1);
    if (packetEnd > packetCapacity || stateEnd > stateCapacity)
      return false;
  }
  for (unsigned i = first; i < last; ++i) {
    auto &byte = packet[3 + std::size_t(i) * packetStride];
    auto *value = state + std::size_t(i) * stateStride;
    if (read)
      byte = value[0];
    else if (operation == Transfer::WriteByte)
      value[0] = byte;
    else {
      value[0] = byte;
      value[1] = value[2] = value[3] = 0;
    }
  }
  if (read) {
    packet[2] =
        static_cast<std::uint8_t>((std::uint32_t(last) - first) * packetStride);
    packet[1] &= 0x7f;
  }
  return true;
}

bool applyParameterPacket(std::uint8_t *packet, std::size_t packetCapacity,
                          std::uint8_t *context, std::size_t contextCapacity,
                          std::uint8_t boardId) {
  if (!packet || packetCapacity < 3)
    return false;
  const unsigned command = packet[1] & 0x7f;
  if (command != 0x21 && command != 0x23 && command != 0x29 && command != 0x2a)
    return false;
  const unsigned destination = packet[0] >> 4;
  if (destination != boardId && destination != 15)
    return true;
  const bool read = (packet[1] & 0x80) != 0;
  if (!read && (command == 0x29 || command == 0x2a))
    return true;
  const unsigned selector = packet[0] & 15;
  const auto first = static_cast<std::uint8_t>(selector == 15 ? 0 : selector);
  const auto last =
      static_cast<std::uint8_t>(selector == 15 ? 4 : selector + 1);
  const bool word = command == 0x29 || command == 0x2a;
  const std::size_t offset = command == 0x21   ? 0x102
                             : command == 0x23 ? 0x103
                             : command == 0x29 ? 0x28
                                               : 0x2c;
  if (!context || offset > contextCapacity)
    return false;
  const auto operation = word   ? Transfer::ReadWordLowByte
                         : read ? Transfer::ReadByte
                                : Transfer::WriteByte;
  return transferStrided(operation, packet, packetCapacity, context + offset,
                         contextCapacity - offset, word ? 64 : 40, 1, first,
                         last);
}
} // namespace presonus::analysis::efm_fader_parameters
