#pragma once
#include <array>
#include <cstdint>

namespace Presonus::DICE {
class SysexPacket;
class Dice3Subsystem;
} // namespace Presonus::DICE
namespace presonus::dice {
// Independent gateway. Product adapter may use upstreamSystemClock; fixtures
// provide raw signed64 values. This is NOT a Core::GetAbsoluteTime definition.
std::int64_t packetClockRawTicks();

struct PacketMetadata {
  std::array<std::uint32_t, 2> headerWords{};
  std::int64_t constructedQuotient = 0;
  std::array<std::uint32_t, 4> trailingWords{};
};
struct SubsystemState {
  unsigned char command = 0;
  unsigned char status = 0;
  std::array<std::uint32_t, 3> infoWords{};
  std::uint32_t rateWord = 0;
  std::uint32_t clockWord = 0;
};
class SubsystemServices {
public:
  virtual ~SubsystemServices() = default;
  virtual void post(Presonus::DICE::SysexPacket &packet) = 0;
  // Raw return-word boundary, observed only as zero versus nonzero by caller.
  virtual std::uint32_t waitAck(Presonus::DICE::Dice3Subsystem &receiver,
                                std::int64_t timeout) = 0;
};
} // namespace presonus::dice
