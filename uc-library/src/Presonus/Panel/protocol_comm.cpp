#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <algorithm>
#include <cstring>

namespace Presonus::Panel {
ProtocolComm::ProtocolComm() {
  // Independent portable initialization, not an original standalone ctor.
  receive_[0] = 0;
  receive_[1] = 0;
  receive_[2] = 0;
}
ProtocolComm::~ProtocolComm() =
    default; // Genuine lock member lifetime exactly once.
int IPanelIO::broadcast(Control *) { return 0; }
int ProtocolComm::readMsg(Uart_Msg_Type &message) {
  Core::Threads::ScopedLock guard(lock_);
  char *pending = receive_.data() + 2;
  char next[2];
  for (;;) {
    if (read(next, 1) != 1)
      return 0;
    next[1] = 0;
    const int count = static_cast<int>(std::strlen(next));
    if (count > 0) {
      const int available = 31 - static_cast<int>(std::strlen(pending));
      if (available > 0) {
        std::strncat(pending, next, std::min(available, count));
        pending[31] = 0;
      }
    }
    const int result = uart_protocol_decode(
        pending, static_cast<unsigned char>(std::strlen(pending)), &message);
    if (result < 0)
      pending[0] = 0;
    else if (result != 0) {
      pending[0] = 0;
      return 1;
    }
  }
}
int ProtocolComm::writeMsg(Uart_Msg_Type &message) {
  Core::Threads::ScopedLock guard(lock_);
  char text[16];
  const int count = uart_protocol_encode(&message, text);
  if (count <= 0)
    return 0;
  return write(text, count) == count ? 1 : 0;
}
} // namespace Presonus::Panel
