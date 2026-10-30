#include "presonus/uc/outgoing_connection.hpp"
namespace Presonus::UC {
void SocketConnection::getAddress(const char *&address,
                                  unsigned short &port) const {
  address = socket_.remoteAddress.str();
  port = socket_.remotePort;
}
OutgoingConnection *OutgoingConnection::cast(Connection *connection) {
  return connection && connection->getType() == 1
             ? static_cast<OutgoingConnection *>(connection)
             : nullptr;
}
int OutgoingConnection::getType() const { return 1; }
} // namespace Presonus::UC
