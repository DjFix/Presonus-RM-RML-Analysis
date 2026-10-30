#include "presonus/noaa/ucnet_handler.hpp"
namespace Presonus::NOAA {
bool TCardUCNetHandler::accepts(const SysexPacket &packet) {
  return packet.length > 1 && packet.bytes[1] > 63;
}
void TCardUCNetHandler::receive(const SysexPacket &packet) {
  if (packet.length <= 1 || packet.bytes[1] != 64)
    return;
  if (packet.length > 4) {
    // Actual writer requires255 valid physical bytes, independently of length.
    // SysexPacket owns256 bytes; forward raw bytes without changing framing.
    state_.incoming.writeMIDI(packet.bytes.data());
    return;
  }
  state_.observedByte8 = 1;
  const auto ticks = state_.clock.clockRawTicks() / 1000000;
  state_.observedWord60 = 1;
  state_.observedTicks70 = ticks;
}
int TCardUCNetHandler::startup(int port) {
  return state_.network.addExternalConnection(state_.connection, state_.channel,
                                              port, 0, nullptr);
}
int TCardUCNetHandler::shutdown() {
  const int result = state_.network.removeExternalConnection(state_.channel);
  state_.connection = nullptr;
  return result;
}
} // namespace Presonus::NOAA
