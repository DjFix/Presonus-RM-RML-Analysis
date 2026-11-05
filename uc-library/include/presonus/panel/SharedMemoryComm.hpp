#pragma once

struct Uart_Msg_Type;

namespace Presonus::Panel {
// Partial portable source port of the four evidenced no-operation methods.
// int is an explicit portable return choice: original return declarations are
// unresolved. No original inheritance, virtual layout, object size,
// constructor, or ARM ABI compatibility is asserted. The global message tag is
// preserved.
class SharedMemoryComm {
public:
  int read(char *, int);
  int write(const char *, int);
  int readMsg(Uart_Msg_Type &);
  int writeMsg(Uart_Msg_Type &);
};
} // namespace Presonus::Panel
