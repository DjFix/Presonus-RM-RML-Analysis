#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/socket_channel.hpp"
namespace Presonus::UC {
SocketConnection::SocketConnection(ConnectionHandler &handler, int type)
    : Connection(handler, type), socket_(ownedSocketState_) {}
SocketConnection::~SocketConnection() {
  if (ownedChannel_) {
    ownedChannel_.reset();
    presonus::uc::ConnectionSourceAccess::transport(*this).bind(nullptr);
  }
}
SocketConnection::Channel::Channel(
    std::unique_ptr<Core::Sockets::Socket> socket)
    : socket_(std::move(socket)),
      ownedIO_{
          socket_.get(),
          [](void *p, void *data, int n, int flags) {
            return static_cast<Core::Sockets::Socket *>(p)->receive(data, n,
                                                                    flags);
          },
          [](void *p, const void *data, int n, int flags) {
            return static_cast<Core::Sockets::Socket *>(p)->sendAll(data, n,
                                                                    flags);
          },
          [](void *p, int timeout) {
            return static_cast<Core::Sockets::Socket *>(p)->isReadable(timeout);
          },
          [](void *p, int timeout) {
            return static_cast<Core::Sockets::Socket *>(p)->isWritable(timeout);
          },
          [](void *p, int timeout) {
            return static_cast<Core::Sockets::Socket *>(p)->isAnyError(timeout);
          },
          [](void *p, int &n) {
            return static_cast<Core::Sockets::Socket *>(p)->getBytesAvailable(
                n);
          }},
      io_(ownedIO_) {}
SocketConnection::Channel::~Channel() = default;
} // namespace Presonus::UC
