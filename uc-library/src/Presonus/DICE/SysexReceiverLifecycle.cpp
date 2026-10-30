#include "../../portable/dice/ReceiverStateGuard.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"

namespace Presonus::DICE {
SysexReceiver::SysexReceiver() {
  presonus::dice::ReceiverStateGuard guard(portableStateLock_);
  state_.command = 0;
  state_.status = 0;
  portableResponseWord_ = 0;
}

void SysexReceiver::post(SysexPacket &packet) {
  {
    presonus::dice::ReceiverStateGuard guard(portableStateLock_);
    portableResponseWord_ = 0;
    state_.command = 0;
    state_.status = 0;
  }
  // Use the pinned source implementation of Core's singleton. This is a
  // source port, not reconstructed Core code or original ARM object layout.
  Dice3Uart::instance().post(packet);
}
} // namespace Presonus::DICE
