#include "core/network/corenetwork.h"
#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/outgoing_connection.hpp"
#include "presonus/uc/report.hpp"
#include <algorithm>
#include <cstring>
namespace Presonus::UC {
OutgoingConnection::OutgoingConnection(ConnectionHandler &handler,
                                       const char *host, unsigned short port,
                                       unsigned short periodicPort)
    : SocketConnection(handler, 2) {
  socket_.remoteAddress = host ? host : "";
  presonus::uc::ConnectionSourceAccess::transport(*this).connectionName =
      socket_.remoteAddress.str();
  socket_.remotePort = port;
  socket_.periodicPort = periodicPort;
}
OutgoingConnection::~OutgoingConnection() { deactivate(); }
bool OutgoingConnection::activate() {
  if (ownedChannel_)
    return true;
  UCReportMessage(0, "Resolving hostname %s...", socket_.remoteAddress.str());
  auto &address = socket_.resolvedAddress;
  if (!Core::Sockets::Network::getAddressByHost(address,
                                                socket_.remoteAddress.str()))
    return false;
  address.port = socket_.remotePort;
  UCReportMessage(0, "Connecting to %s...", socket_.remoteAddress.str());
  auto socket = std::make_unique<Core::Sockets::Socket>(
      Core::Sockets::kInternet, Core::Sockets::kStream, Core::Sockets::kTCP);
  (void)socket->getDescriptor();
  socket->setOption(Core::Sockets::SocketOption::kNonBlocking, 1);
  socket->connect(address); // Native ignores nonblocking connect's result.
  auto channel = std::make_unique<Channel>(std::move(socket));
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  provider.bind(channel.get());
  ownedChannel_ = std::move(channel);
  return true;
}
void OutgoingConnection::deactivate() {
  if (!ownedChannel_)
    return;
  ownedChannel_->sourceSocket()->disconnect();
  ownedChannel_.reset();
  presonus::uc::ConnectionSourceAccess::transport(*this).bind(nullptr);
}
bool OutgoingConnection::reset() {
  ++retries_;
  if (static_cast<std::int32_t>(retries_) > 3)
    return false;
  deactivate();
  presonus::uc::ConnectionSourceAccess::transport(*this).failed = false;
  return true;
}
bool OutgoingConnection::process(bool drain) {
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  if (!ownedChannel_ && hasQueuedEvents())
    activate();
  // Both native inactive branches join here, including failed activation.
  Connection::process(drain);
  if (ownedChannel_ && ownedChannel_->hasErrors(1)) {
    UCReportMessage(0, "Outgoing socket is in error state!!!", 0);
    provider.failed = true;
  }
  return !provider.failed;
}
} // namespace Presonus::UC
