#include "presonus/noaa/sysex_receiver.hpp"

namespace Presonus::NOAA {
SysexReceiver::SysexReceiver() {
  state_.command = 0;
  state_.status = 0;
  state_.infoWords[0] = 0;
}

void SysexReceiver::receive(const SysexPacket &packet) {
  const unsigned char command = packet.length > 1 ? packet.bytes[1] : 0;
  if ((command >= 0x12 && command <= 0x14) || command == 0x41)
    return;
  state_.command = command;
  // Physical packet storage exists even when its logical length is <3.
  state_.status = packet.bytes[2];
}

void SysexReceiver::post(SysexPacket &packet) {
  state_.infoWords[0] = 0;
  state_.command = 0;
  state_.status = 0;
  TCardSPI::instance().post(packet);
}
} // namespace Presonus::NOAA
