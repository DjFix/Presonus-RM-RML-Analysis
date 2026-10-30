#pragma once
#include "core/system/corethread.h"
#include <array>

// Original global type identity; storage/layout definition belongs to the
// separately evidenced application codec, not to the transport subclass.
struct Uart_Msg_Type;
namespace presonus::panel {
struct ProtocolCommAccess;
}

namespace Presonus {
// Original RTTI root and two pure slots. Ordinary numeric return spelling is a
// portable contract, declaration-pending. No virtual destructor slot exists.
class IPanelPort {
public:
  virtual int readMsg(Uart_Msg_Type &) = 0;
  virtual int writeMsg(Uart_Msg_Type &) = 0;

protected:
  ~IPanelPort() = default; // Independent protected nonvirtual lifetime helper.
};
namespace Panel {
class Control;
class IPanelIO : public IPanelPort {
public:
  virtual int broadcast(Control *);
  virtual int open(const char *) = 0;
  virtual void close() = 0;
  virtual int enableHISpeed(bool) = 0;

protected:
  ~IPanelIO() = default; // Independent helper, never invents destructor slots.
};
class ProtocolComm : public IPanelIO {
public:
  // Portable initialization inferred from UART's inlined base setup; no
  // separate original ProtocolComm constructor symbol is claimed recovered.
  ProtocolComm();
  ProtocolComm(const ProtocolComm &) = delete;
  ProtocolComm &operator=(const ProtocolComm &) = delete;
  int readMsg(Uart_Msg_Type &) override;
  int writeMsg(Uart_Msg_Type &) override;
  virtual ~ProtocolComm();                  // Proven original slots6/7 D1/D0.
  virtual int write(const char *, int) = 0; // Original slot8.
  virtual int read(char *, int) = 0;        // Original slot9.
protected:
  // The one genuine recursive CCL lock is shared with UART subclass methods.
  // Base lifetime owns construction/destruction; never destroy it twice.
  Core::Threads::Lock lock_;

private:
  // Portable storage, not ARM layout. The original 32-byte receive string is
  // preceded by the high byte of its ARM vptr (zero in both supplied ELFs).
  // Two explicit prefix bytes permit defined zero-length/short-K codec reads.
  // Their default zero state is a portable choice, not role-specific ARM vptr
  // equivalence; legacy malformed-prefix domains require an explicit seed.
  std::array<char, 34> receive_;
  friend struct presonus::panel::ProtocolCommAccess;
};
} // namespace Panel
} // namespace Presonus

namespace presonus::panel {
// Independent access for source-port state fixtures; no original symbol claim.
struct ProtocolCommAccess {
  static char *receive(Presonus::Panel::ProtocolComm &value) {
    return value.receive_.data() + 2;
  }
  static Core::Threads::Lock &lock(Presonus::Panel::ProtocolComm &value) {
    return value.lock_;
  }
  static void prefix(Presonus::Panel::ProtocolComm &value, char a, char b) {
    value.receive_[0] = a;
    value.receive_[1] = b;
  }
};
} // namespace presonus::panel
