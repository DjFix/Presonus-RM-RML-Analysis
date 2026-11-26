#include "presonus/avb/noaa_manager_transport.hpp"
#include <stdexcept>
namespace {
// Observe the real singleton without creating or opening a missing device.
struct SpiSingletonAccess : Presonus::NOAA::TCardSPI {
  static auto *current() { return theInstance; }
};
} // namespace
namespace presonus::avb {
NoaaManagerTransport::NoaaManagerTransport(
    Presonus::AVB::AvbManagerBase &manager, Presonus::NOAA::TCardSPI &spi,
    dice::IdlePump &pump)
    : ManagerTransport(manager, Presonus::AVB::AvbManagerBase::Role::RmServer,
                       pump),
      spi_(spi), receiver_(*this) {
  if (SpiSingletonAccess::current() != &spi)
    throw std::logic_error("AVB requires initialized NOAA singleton");
  receiver_.setPortableResponseServices(services_);
  spi_.registerReceiver(&receiver_);
}
NoaaManagerTransport::~NoaaManagerTransport() {
  spi_.unRegisterReceiver(&receiver_);
}
bool NoaaManagerTransport::Receiver::accepts(
    const Presonus::NOAA::SysexPacket &packet) {
  return owner_.manager_.accepts(packet);
}
void NoaaManagerTransport::Receiver::receive(
    const Presonus::NOAA::SysexPacket &packet) {
  owner_.receivePacket(packet);
  const auto response = owner_.responseState();
  portableState().command = response.command;
  portableState().status = response.status;
}
int NoaaManagerTransport::postAndWait(unsigned char *bytes,
                                      unsigned char length) {
  if (SpiSingletonAccess::current() != &spi_)
    throw std::logic_error("AVB NOAA binding changed");
  Presonus::NOAA::SysexPacket packet(bytes, length);
  receiver_.post(packet);
  receiver_.waitAck(500);
  return receiver_.portableState().status == 1 ? 0 : -1;
}
} // namespace presonus::avb
