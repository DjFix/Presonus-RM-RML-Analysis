#include "core/system/coredebug.h"
#include "presonus/noaa/card.hpp"
namespace Presonus::NOAA {
unsigned char TCard::sendSampleRate(int rate, int link) {
  Core::DebugPrintf("NOAA: sendSampleRate rate:%d linkID:%d\n", rate, link);
  const auto board = state_.observedWord3c;
  if (static_cast<std::uint32_t>(board - 23u) <= 1u) {
    const unsigned char delay = rate > 1 ? 1 : 0;
    const unsigned char bytes[] = {0xf0, 0x21, delay, 0xf7};
    SysexPacket packet(bytes, 4);
    post(packet);
    waitAck(500);
    Core::DebugPrintf("Rack main out timing workaround applied.  Delay = %d\n",
                      int(delay));
  }
  const unsigned char bytes[] = {
      0xf0, 0x11,
      static_cast<unsigned char>(static_cast<unsigned int>(rate) & 0x7f),
      static_cast<unsigned char>(static_cast<unsigned int>(link) & 0x7f), 0xf7};
  SysexPacket packet(bytes, 5);
  post(packet);
  return waitAck(500);
}
} // namespace Presonus::NOAA
