#include "presonus/noaa/ucnet_handler.hpp"
#include <algorithm>
#include <stdexcept>
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
namespace {
// Compare signed high words then unsigned low words, exactly as ARM cmp/bgt.
// Unsigned addition retains native wrap without signed-overflow undefined
// behavior.
bool after(std::uint64_t now, std::uint64_t deadline) {
  const auto nh = static_cast<std::uint32_t>(now >> 32) ^ 0x80000000u;
  const auto dh = static_cast<std::uint32_t>(deadline >> 32) ^ 0x80000000u;
  return nh > dh || (nh == dh && static_cast<std::uint32_t>(now) >
                                     static_cast<std::uint32_t>(deadline));
}
} // namespace
void TCardUCNetHandler::idleIO() {
  const auto now = [&] { return state_.clock.clockRawTicks() / 1000000; };
  if (state_.observedWord60 != 0) {
    if (!state_.outgoing || state_.outgoing == &state_.incoming)
      throw std::logic_error("idleIO requires a distinct outgoing queue");
    for (unsigned count = 0; count < 6 && !state_.outgoing->isEmpty();
         ++count) {
      SysexPacket packet;
      std::fill_n(packet.bytes.begin(), 255, static_cast<unsigned char>(0x45));
      packet.portableMetadata().constructedQuotient = now();
      state_.outgoing->readMIDI(packet.bytes.data(), packet.length);
      TCardSPI::instance().post(packet);
    }
    // ELF C.149 = f0 40 f7. Inline construction reads time before and after
    // copy.
    SysexPacket packet;
    packet.length = 3;
    std::fill_n(packet.bytes.begin(), 255, static_cast<unsigned char>(0x45));
    packet.portableMetadata().constructedQuotient = now();
    packet.bytes[0] = 0xf0;
    packet.bytes[1] = 0x40;
    packet.bytes[2] = 0xf7;
    packet.portableMetadata().constructedQuotient = now();
    TCardSPI::instance().post(packet);
    state_.observedTicks68 = static_cast<std::uint64_t>(now());
    state_.observedWord60 = 0;
    return;
  }
  const auto ticks = static_cast<std::uint64_t>(now());
  if (after(ticks, state_.observedTicks68 + 400)) {
    state_.observedTicks68 = ticks;
    // ELF C.148 = f0 40 f7. Actual provider constructor performs two clock
    // reads.
    const unsigned char bytes[]{0xf0, 0x40, 0xf7};
    SysexPacket packet(bytes, 3);
    TCardSPI::instance().post(packet);
  }
  if (after(ticks, static_cast<std::uint64_t>(state_.observedTicks70) + 5000))
    state_.observedByte8 = 0;
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
