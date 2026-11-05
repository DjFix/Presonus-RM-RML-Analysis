#include "presonus/panel/SharedMemoryComm.hpp"

namespace Presonus::Panel {
// Every supplied client/server body sets r0 to zero without accessing this or
// argument memory. These are observed original no-operations, not transport
// placeholders for a presumed implementation.
int SharedMemoryComm::read(char *, int) { return 0; }
int SharedMemoryComm::write(const char *, int) { return 0; }
int SharedMemoryComm::readMsg(Uart_Msg_Type &) { return 0; }
int SharedMemoryComm::writeMsg(Uart_Msg_Type &) { return 0; }
} // namespace Presonus::Panel
