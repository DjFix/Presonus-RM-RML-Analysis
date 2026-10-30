#include "presonus/embedded_efm/efm_version_packet.hpp"

namespace presonus::analysis::efm_fader_app {
bool applyVersionPacket(std::uint8_t *packet, std::size_t capacity,
                        std::uint8_t boardId) {
  if (!packet || capacity < 3 || (packet[1] & 0x7f) != 0x25)
    return false;
  const unsigned destination = packet[0] >> 4;
  if (destination != boardId && destination != 15)
    return true;
  if (!(packet[1] & 0x80))
    return true;
  const unsigned selector = packet[0] & 15;
  const unsigned start = selector == 15 ? 0 : selector;
  const unsigned end = selector == 15 ? 4 : selector + 1;
  if (capacity < 3 + end)
    return false;
  for (unsigned i = start; i < end; ++i)
    packet[3 + i] = 0x1b;
  packet[2] = static_cast<std::uint8_t>(end - start);
  packet[1] &= 0x7f;
  return true;
}
} // namespace presonus::analysis::efm_fader_app
