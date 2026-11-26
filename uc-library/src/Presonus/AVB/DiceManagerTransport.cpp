#include "presonus/avb/dice_manager_transport.hpp"
#include <stdexcept>
namespace {
// Observe the real singleton without creating or opening a missing device.
struct UartSingletonAccess : Presonus::DICE::Dice3Uart {
  static auto *current() { return theInstance; }
};
} // namespace
namespace presonus::avb {
DiceManagerTransport::DiceManagerTransport(
    Presonus::AVB::AvbManagerBase &manager, Presonus::DICE::Dice3Uart &uart,
    dice::IdlePump &pump)
    : ManagerTransport(manager, Presonus::AVB::AvbManagerBase::Role::Cs18Client,
                       pump),
      uart_(uart), receiver_(*this) {
  if (UartSingletonAccess::current() != &uart)
    throw std::logic_error("AVB requires initialized DICE singleton");
  receiver_.setPortableResponseServices(services_);
  uart_.registerReceiver(&receiver_);
}
DiceManagerTransport::~DiceManagerTransport() {
  uart_.unRegisterReceiver(&receiver_);
}
bool DiceManagerTransport::Receiver::accepts(
    const Presonus::DICE::SysexPacket &packet) {
  return owner_.manager_.accepts(packet);
}
void DiceManagerTransport::Receiver::receive(
    const Presonus::DICE::SysexPacket &packet) {
  owner_.receivePacket(packet);
  const auto response = owner_.responseState();
  portableState().command = response.command;
  portableState().status = response.status;
}
int DiceManagerTransport::postAndWait(unsigned char *bytes,
                                      unsigned char length) {
  if (UartSingletonAccess::current() != &uart_)
    throw std::logic_error("AVB DICE binding changed");
  Presonus::DICE::SysexPacket packet(bytes, length);
  receiver_.post(packet);
  receiver_.waitAck(500);
  return receiver_.snapshotPortableState().status == 1 ? 0 : -1;
}
} // namespace presonus::avb
