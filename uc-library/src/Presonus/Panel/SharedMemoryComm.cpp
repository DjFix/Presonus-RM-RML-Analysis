#include "presonus/panel/SharedMemoryComm.hpp"

namespace Presonus::Panel {
// The read/write client/server bodies set r0 to zero without accessing this or
// argument memory. These are observed original no-operations, not transport
// placeholders for a presumed implementation.
int SharedMemoryComm::read(char *, int) { return 0; }
int SharedMemoryComm::write(const char *, int) { return 0; }
int SharedMemoryComm::readMsg(Uart_Msg_Type &) { return 0; }
int SharedMemoryComm::writeMsg(Uart_Msg_Type &) { return 0; }
void SharedMemoryComm::close() {}
} // namespace Presonus::Panel
