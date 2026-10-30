#include "core/system/coredebug.h"
#include "presonus/dice/codec.hpp"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/card.hpp"
#include <stdexcept>
namespace {
Presonus::Dsp::IAudioHAL &requiredHal(presonus::noaa::CardState &state) {
  if (!state.audioHal ||
      static_cast<const void *>(state.audioHal) != state.opaque5c.value)
    throw std::logic_error(
        "TCard requires a live matching typed audio HAL binding");
  return *state.audioHal;
}
std::uint32_t expectedSerial(presonus::noaa::CardState &state) {
  if (!state.expectedSerial)
    throw std::logic_error(
        "TCard info requires an explicit expected serial binding");
  return *state.expectedSerial;
}
} // namespace
namespace Presonus::NOAA {
void TCard::receive(const SysexPacket &packet) {
  // Original function-local data identity. Pointer width and const declarations
  // are source-port choices; original table bytes/targets are tracked
  // separately.
  [[gnu::used]] static const char *gErrStatusNames[] = {
      "SPI_TX overflow",      "SPI_TX too long",    "SPI_RX_DICE overflow",
      "SPI_RX_DICE too long", "SPI_RX_PC overflow", "SPI_RX_PC too long",
      "SPI_RX_IC overflow",   "SPI_RX_IC too long"};
  const unsigned char command = packet.length > 1 ? packet.bytes[1] : 0;
  if (!((command >= 0x12 && command <= 0x14) || command == 0x41)) {
    portableState().command = command;
    portableState().status = packet.bytes[2];
  }
  state_.observedWord44 = 1;
  if (packet.length <= 1)
    return;
  switch (packet.bytes[1]) {
  case 1:
    state_.observedWord18 = packet.bytes[2] != 0;
    state_.observedWord20 = unpack32(packet.bytes.data() + 3);
    state_.observedWord24 = unpack32(packet.bytes.data() + 8);
    state_.observedWord28 = unpack32(packet.bytes.data() + 13) & 0xffff0000u;
    state_.observedWord34 = unpack32(packet.bytes.data() + 18);
    state_.observedWord38 = unpack32(packet.bytes.data() + 23);
    state_.observedWord14 = unpack32(packet.bytes.data() + 28);
    state_.observedWord3c = packet.bytes[33];
    Core::DebugPrintf("Detected IO Card: %s\n", getCardCString());
    {
      const auto expected = expectedSerial(state_);
      Core::DebugPrintf("read serialnumbner:0x%8X expected number:0x%8X\n",
                        state_.observedWord34, expected);
    }
    Core::DebugPrintf("read productID:0x%2X expected:0x%2X\n",
                      state_.observedWord3c, state_.observedWord30);
    if (state_.observedWord34 == expectedSerial(state_) &&
        state_.observedWord3c == state_.observedWord30)
      state_.observedWord1c = 1;
    else {
      state_.observedWord1c = 0;
      Core::DebugPrintf("Invalid Serial Issue\n");
    }
    break;
  case 18:
    state_.observedWord40 = 0;
    if (state_.observedWord18 != 0 && state_.opaque5c.value != nullptr) {
      requiredHal(state_).enableDACs(false, false, 2);
      Core::DebugPrintf("NOAA: %s\n", "RMUTE_START_COMMAND - DACs are MUTED!");
    }
    break;
  case 19:
    state_.observedWord40 = 1;
    if (state_.opaque5c.value != nullptr)
      requiredHal(state_).enableDACs(true, packet.bytes[2] > 1, 2);
    geqInit(9, 1);
    break;
  case 24:
    for (unsigned index = 0; index < 8; ++index)
      if (packet.bytes[2 + index] != 0) {
        Core::DebugPrintf("NOAA: STAT\n");
        Core::DebugPrintf("%s=%d\n", gErrStatusNames[index],
                          int(packet.bytes[2 + index]));
      }
    break;
  case 20:
    state_.observedWord4c = packet.bytes[2];
    state_.observedWord50 = packet.bytes[3];
    state_.observedWord54 = packet.bytes[4];
    state_.observedWord58 = packet.bytes[5];
    Core::DebugPrintf(
        "NOAA: LINK_MODE_COMMAND type:%d id=%d delay=%d count=%d\n",
        int(state_.observedWord4c), int(state_.observedWord50),
        int(state_.observedWord54), int(state_.observedWord58));
    break;
  case 27:
    if (packet.bytes[2] == 3)
      state_.observedByte48 = 1;
    else if (packet.bytes[2] == 4)
      state_.observedByte48 = 0;
    break;
  default:
    break;
  }
}
} // namespace Presonus::NOAA
