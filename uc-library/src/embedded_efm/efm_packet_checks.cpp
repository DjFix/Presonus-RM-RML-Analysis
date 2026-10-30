#include "presonus/embedded_efm/efm_packet_checks.hpp"

namespace presonus::analysis::efm_fader_app {
namespace {
void checks(const std::uint8_t *packet, std::size_t count, unsigned &a,
            unsigned &b) {
  a = b = 0;
  for (std::size_t i = 0; i < count; ++i) {
    a = (a + packet[i]) % 255;
    b = (b + a) % 255;
  }
}
} // namespace
bool appendPacketChecks(std::uint8_t *packet, std::size_t capacity) {
  if (!packet || capacity < 3)
    return false;
  const std::size_t count = 3 + packet[2];
  if (capacity < count + 2)
    return false;
  unsigned a, b;
  checks(packet, count, a, b);
  packet[count] = static_cast<std::uint8_t>(a);
  packet[count + 1] = static_cast<std::uint8_t>(b);
  return true;
}
bool validatePacketChecks(const std::uint8_t *packet, std::size_t capacity,
                          unsigned &originalResult) {
  if (!packet || capacity < 3)
    return false;
  const std::size_t count = packet[1] > 0x7f ? 3 : 3 + packet[2];
  if (capacity < count + 2)
    return false;
  unsigned a, b;
  checks(packet, count, a, b);
  originalResult = (packet[count] != a) | (packet[count + 1] != b);
  return true;
}
} // namespace presonus::analysis::efm_fader_app
