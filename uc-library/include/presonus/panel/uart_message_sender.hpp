#pragma once
#include "presonus/panel/protocol_comm.hpp"

namespace Presonus {
// Partial portable source model, not the original layout/inheritance/vtable.
// The original slot0 declaration is unresolved and is deliberately not named.
class UARTMessageSender {
public:
  // Independent source-port initialization, not an original ctor recovery.
  explicit UARTMessageSender(IPanelPort &port) : port_(port) {}
  // Parameter/member identities are encoded and observed. Void returns remain
  // provisional: ordinary mangling does not encode the original return types.
  void setFaderPosition(int, int);
  void setDigitalPot(int, int, int);
  void setLedMeterPosition(int, int, int);
  void setLedMeterPositionCA(int, int, int);
  void setLedMeterClip(int, int);

private:
  IPanelPort &port_; // Independent borrowed real provider, not an ARM field.
};
} // namespace Presonus
