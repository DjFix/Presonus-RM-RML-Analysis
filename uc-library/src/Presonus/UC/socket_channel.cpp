#include "presonus/uc/socket_channel.hpp"
namespace Presonus::UC {
int SocketConnection::Channel::read(void *output, int count) {
  int total = 0;
  auto *bytes = static_cast<unsigned char *>(output);
  while (total < count) {
    const int result =
        io_.receive(io_.context, bytes + total, count - total, 0);
    if (result < 0) {
      if (total == 0)
        total = result;
      break;
    }
    total += result;
  }
  return total;
}
int SocketConnection::Channel::write(const void *input, int count) {
  return io_.sendAll(io_.context, input, count, 0);
}
bool SocketConnection::Channel::isReadable(int timeout) {
  return io_.readable(io_.context, timeout);
}
bool SocketConnection::Channel::isWritable(int timeout) {
  return io_.writable(io_.context, timeout);
}
bool SocketConnection::Channel::hasErrors(int timeout) {
  return io_.error(io_.context, timeout);
}
int SocketConnection::Channel::getBytesAvailable() {
  int count = 0;
  io_.available(io_.context, count);
  return count;
}
int SocketConnection::Channel::getGranularity() { return 4096; }
} // namespace Presonus::UC
