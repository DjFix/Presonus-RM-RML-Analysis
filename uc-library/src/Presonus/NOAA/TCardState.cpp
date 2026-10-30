#include "presonus/noaa/card.hpp"
namespace Presonus::NOAA {
bool TCard::accepts(const SysexPacket &packet) {
  if (packet.length <= 1)
    return false;
  switch (packet.bytes[1]) {
  case 1:
  case 9:
  case 17:
  case 18:
  case 19:
  case 20:
  case 24:
  case 27:
  case 28:
  case 40:
    return true;
  default:
    return false;
  }
}
bool TCard::isMounted() { return state_.observedWord44 != 0; }
unsigned char TCard::isDesktopConnected() { return state_.observedByte48; }
const char *TCard::getCardCString() {
  switch (state_.observedWord14) {
  case 0xffffffffu:
    return "Unknown";
  case 0:
    return "NOAA";
  case 1:
    return "NIMH";
  case 2:
    return "ESA";
  default:
    return nullptr;
  }
}
} // namespace Presonus::NOAA
