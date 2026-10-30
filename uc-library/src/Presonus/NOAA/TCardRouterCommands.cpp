#include "../../portable/noaa/RouterHelpers.hpp"
#include "presonus/noaa/router.hpp"
#include <stdexcept>
namespace Presonus::NOAA {
// Original internal-linkage symbol remains64bytes. Const/type spelling is a
// portable choice; identity/size/native bytes do not prove its old declaration.
static const unsigned char g64RouteTable[64] = {
    0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x01, 0x09, 0x11,
    0x19, 0x21, 0x29, 0x31, 0x39, 0x02, 0x0a, 0x12, 0x1a, 0x22, 0x2a,
    0x32, 0x3a, 0x03, 0x0b, 0x13, 0x1b, 0x23, 0x2b, 0x33, 0x3b, 0x04,
    0x0c, 0x14, 0x1c, 0x24, 0x2c, 0x34, 0x3c, 0x05, 0x0d, 0x15, 0x1d,
    0x25, 0x2d, 0x35, 0x3d, 0x06, 0x0e, 0x16, 0x1e, 0x26, 0x2e, 0x36,
    0x3e, 0x07, 0x0f, 0x17, 0x1f, 0x27, 0x2f, 0x37, 0x3f};
bool TCardRouter::accepts(const SysexPacket &packet) {
  return packet.length > 1 && packet.bytes[1] == 0x16;
}
void TCardRouter::doRouteCommands(DiceRoute *routes, int count,
                                  unsigned char remap) {
  // Independent guard, outside equivalence: original count578 first overwrites
  // its CoreLock at+0x920. Counts64/65 intentionally remain accepted and
  // preserve adjacent app writes plus transmitted length wrap3/7.
  if (count > 577)
    throw std::length_error("Router command writes original Core region");
  if (count > 0 && routes == nullptr)
    throw std::invalid_argument("Positive route count requires readable input");
  auto &bytes = state_.applicationBytes;
  bytes[0] = 0xf0;
  bytes[1] = 0x16;
  const auto size = count > 0 ? static_cast<std::size_t>(count) : 0;
  // Access object representation as bytes, preserving load-before-store even
  // when caller input aliases its independent application-byte storage.
  const auto *input = reinterpret_cast<const unsigned char *>(routes);
  for (std::size_t i = 0; i < size; ++i) {
    const auto device0 = input[4 * i];
    auto channel0 = input[4 * i + 1];
    const auto device1 = input[4 * i + 2];
    auto channel1 = input[4 * i + 3];
    if (remap) {
      if (device0 == 0)
        channel0 = presonus::noaa::mapRouterChannel(channel0, lookup_);
      if (device1 == 0)
        channel1 = presonus::noaa::mapRouterChannel(channel1, lookup_);
    }
    bytes[2 + 4 * i] = device0 & 0x7f;
    bytes[3 + 4 * i] = channel0 & 0x7f;
    bytes[4 + 4 * i] = device1 & 0x7f;
    bytes[5 + 4 * i] = channel1 & 0x7f;
  }
  bytes[2 + 4 * size] = 0xf7;
  SysexPacket packet(bytes.data(),
                     static_cast<unsigned char>((4 * size + 3) & 255));
  post(packet);
  if (!waitAck(500) || !portableState().status)
    diagnostics_.diagnostic(false, "route err found", 0, false);
}
} // namespace Presonus::NOAA

namespace presonus::noaa {
unsigned char mapRouterChannel(unsigned char channel,
                               const RouterLookupImage &lookup) {
  return channel < 64 ? Presonus::NOAA::g64RouteTable[channel]
                      : lookup.adjacentApplicationData[channel - 64];
}
} // namespace presonus::noaa
