#pragma once

struct Uart_Msg_Type;

namespace Presonus::Panel {
// Partial portable source port of the evidenced no-operation methods.
// int is an explicit portable return choice: original return declarations are
// unresolved. No original inheritance, virtual layout, object size,
// constructor, or ARM ABI compatibility is asserted. The global message tag is
// preserved.
class SharedMemoryComm {
public:
  int enableHISpeed(bool);
  int open(const char *);
  int read(char *, int);
  int write(const char *, int);
  int readMsg(Uart_Msg_Type &);
  int writeMsg(Uart_Msg_Type &);
  // void is a portable choice; the original return declaration is unresolved.
  void close();
};
} // namespace Presonus::Panel
