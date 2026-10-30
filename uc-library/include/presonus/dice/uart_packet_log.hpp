#pragma once
#include "presonus/dice/uart_assembly.hpp"

namespace presonus::dice {
// Independent adapter replacing the formerly borrowed application log boundary.
class CclPacketLogSink final : public PacketLogSink {
public:
  void log(const Presonus::DICE::SysexPacket &packet) override;
};
} // namespace presonus::dice
