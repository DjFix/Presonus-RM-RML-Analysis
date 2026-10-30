#include "../../portable/dice/ReceiverStateGuard.hpp"
#include "presonus/dice/sysex.hpp"
namespace Presonus::DICE {
void SysexReceiver::setPortableStateLock(Core::Threads::Lock *lock) {
  // Setup-only binding, completed before receiver publication.
  portableStateLock_ = lock;
}
presonus::dice::SubsystemState SysexReceiver::snapshotPortableState() const {
  presonus::dice::ReceiverStateGuard guard(portableStateLock_);
  return state_;
}
void SysexReceiver::markPortableInfoPending() {
  presonus::dice::ReceiverStateGuard guard(portableStateLock_);
  state_.infoWords[0] = 0xffffffffU;
}

void SysexReceiver::receive(const SysexPacket &packet) {
  presonus::dice::ReceiverStateGuard guard(portableStateLock_);
  state_.command = packet.length > 1 ? packet.bytes[1] : 0;
  state_.status = packet.bytes[2];
}
} // namespace Presonus::DICE
