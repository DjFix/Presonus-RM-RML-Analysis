#include "presonus/uc/DicePacketQueue.hpp"

namespace Presonus::UC {
bool DicePacketQueue::fromMIDI(Packet &packet, const unsigned char *midi) {
  packet.length = 0;
  if (midi[0] != 0xf0 || midi[1] != 0x40 || midi[2] > 3)
    return false;
  const auto padding = std::int32_t(midi[2]);
  unsigned input = 3;
  for (unsigned output = 0; output < 200; output += 4) {
    unsigned char group[5]{};
    for (unsigned i = 0; i < 5; ++i) {
      if (input > 254 || midi[input] == 0xf7) {
        packet.length = std::int32_t(output) - padding;
        return true;
      }
      group[i] = midi[input++];
    }
    const std::uint32_t word =
        (std::uint32_t(group[0]) << 25) | (std::uint32_t(group[1]) << 18) |
        (std::uint32_t(group[2]) << 11) | (std::uint32_t(group[3]) << 4) |
        (std::uint32_t(group[4]) & 15);
    for (unsigned i = 0; i < 4; ++i)
      packet.bytes[output + i] = static_cast<unsigned char>(word >> (i * 8));
  }
  packet.length = 200 - padding;
  return true;
}

bool DicePacketQueue::toMIDI(const Packet &packet, unsigned char *midi,
                             unsigned char &length) {
  if (packet.length <= 0)
    return false;
  const auto remainder = static_cast<unsigned>(packet.length) & 3;
  midi[0] = 0xf0;
  midi[1] = 0x40;
  midi[2] = static_cast<unsigned char>(remainder ? 4 - remainder : 0);
  unsigned output = 3;
  unsigned input = 0;
  do {
    const std::uint32_t word = std::uint32_t(packet.bytes[input]) |
                               (std::uint32_t(packet.bytes[input + 1]) << 8) |
                               (std::uint32_t(packet.bytes[input + 2]) << 16) |
                               (std::uint32_t(packet.bytes[input + 3]) << 24);
    midi[output] = static_cast<unsigned char>(word >> 25);
    midi[output + 1] = static_cast<unsigned char>((word >> 18) & 127);
    midi[output + 2] = static_cast<unsigned char>((word >> 11) & 127);
    midi[output + 3] = static_cast<unsigned char>((word >> 4) & 127);
    midi[output + 4] = static_cast<unsigned char>(word & 15);
    input += 4;
    output += 5;
  } while (std::int32_t(input) < packet.length && output <= 250);
  if (output <= 254)
    midi[output++] = 0xf7;
  length = static_cast<unsigned char>(output);
  return true;
}
} // namespace Presonus::UC
