#include "core/system/coredebug.h"
#include "presonus/noaa/card.hpp"
namespace Presonus::NOAA {
unsigned char TCard::doCommand(unsigned char command, const char *notice) {
  const unsigned char data[] = {
      0xf0, static_cast<unsigned char>(command & 0x7f), 0xf7};
  SysexPacket packet(data, 3);
  post(packet);
  if (notice && *notice)
    Core::DebugPrintf("NOAA: %s\n", notice);
  return waitAck(500);
}
unsigned char TCard::setClockSource(int clock) {
  Core::DebugPrintf("TCARD: Setting clock source to %d\n", clock);
  const auto low = static_cast<unsigned int>(clock) & 0xff;
  const unsigned char data[] = {0xf0, 0x28,
                                static_cast<unsigned char>(low >> 4),
                                static_cast<unsigned char>(low & 0xf), 0xf7};
  SysexPacket packet(data, 5);
  post(packet);
  return waitAck(500);
}
unsigned char TCard::geqInit(unsigned char slot, unsigned char mode) {
  state_.commandShadow[0] = 0xf0;
  state_.commandShadow[1] = 0x1c;
  state_.commandShadow[3] = slot & 0x7f;
  state_.commandShadow[4] = mode & 0x7f;
  state_.commandShadow[5] = 1;
  state_.commandShadow[6] = 0xf7;
  state_.commandShadow[2] = 1;
  SysexPacket packet(state_.commandShadow.data(), 7);
  post(packet);
  return waitAck(500);
}
} // namespace Presonus::NOAA
