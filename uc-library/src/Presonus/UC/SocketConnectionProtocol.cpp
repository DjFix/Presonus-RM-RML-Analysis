#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/MulticastDatagramProvider.hpp"
#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/report.hpp"
#include <stdexcept>
namespace Presonus::UC {
bool SocketConnection::handleInternal(const Event &event) {
  if (event.type != 21837)
    return Connection::handleInternal(event);
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  const auto found = provider.mappingPorts.find(&event);
  if (found == provider.mappingPorts.end())
    throw std::logic_error("live typed UDPMappingEvent provenance required");
  socket_.periodicPort = found->second;
  UCReportMessage(0, "UDP mapping for %s set to %d",
                  socket_.remoteAddress.str(), socket_.periodicPort);
  return true;
}
bool SocketConnection::sendPeriodicEvent(const Event &event) {
  // Native returns true even when no active channel/UDP port, and ignores
  // the datagram send result. The provider still performs the actual send.
  if (!ownedChannel_ || socket_.periodicPort == 0) {
    UCReportMessage(0, "Can't send periodic event to %s!!!",
                    socket_.remoteAddress.str());
    return true;
  }
  auto address = socket_.resolvedAddress;
  address.port = socket_.periodicPort;
  auto &handler = presonus::uc::ConnectionSourceAccess::handler(*this);
  auto *multicast = handler.getMulticastConnection();
  if (!multicast)
    throw std::logic_error("actual multicast provider required");
  presonus::uc::MulticastDatagramProvider(*multicast).sendTo(address, event);
  return true;
}
} // namespace Presonus::UC
