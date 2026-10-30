#include "presonus/dice/sysex.hpp"

namespace Presonus::DICE {
bool Dice3Subsystem::accepts(const SysexPacket &packet) {
  if (packet.length <= 1)
    return false;
  const auto command = packet.bytes[1];
  if (command > 22)
    return false;
  return ((1u << command) & 0x00400202u) != 0;
}
} // namespace Presonus::DICE
