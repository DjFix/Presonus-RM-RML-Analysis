#include "presonus/dice/uart_packet_log.hpp"

namespace presonus::dice {
void CclPacketLogSink::log(const Presonus::DICE::SysexPacket &packet) {
  packet.log();
}
} // namespace presonus::dice
