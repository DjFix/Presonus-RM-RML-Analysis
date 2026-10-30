#pragma once
#include "core/portable/coretypeinfo.h"
#include "presonus/panel/uart_message.hpp"

struct Touchscreen_Type; // Original global reference identity; opaque storage.
namespace Presonus {
class UARTMessageHandler : public Core::Portable::TypedObject {
public:
  // Independent source-port initialization; no original ctor symbol is claimed.
  UARTMessageHandler() = default;
  void *castTo(Core::Portable::TypedObject::TypeID) override;
  ~UARTMessageHandler() override;
  // Original virtual slots3..19 in this order. Ordinary void return choices
  // remain declaration-pending; TypedObject comes from actual pinned CCL.
  virtual void processMsg(Uart_Msg_Type &, int);
  virtual void handleSwitch(int, int, bool);
  virtual void handleFader(int, int);
  virtual void handleFaderStatus(int, unsigned char);
  virtual void handlePot(int, int);
  virtual void handleEncoder(int, int);
  virtual void handleTemperature(int, int);
  virtual void handleVersion(int, Uart_Msg_Type &);
  virtual void handleError(int, unsigned short);
  virtual void handleTouchscreen(Touchscreen_Type &);
  virtual void handleMovingFaderMcuStatus(unsigned char, unsigned char,
                                          unsigned char);
  virtual void handleGlobalResponse(int, Uart_Msg_Type &);
  virtual void handleCalibrateTouchscreenProgress(unsigned char,
                                                  unsigned short);
  virtual void handleKeyValue(unsigned char, unsigned short);
  virtual void handleLineSense(int, int, int);
  virtual void handleFaderSensitivity(unsigned short);
  virtual void handleFaderSpeed(unsigned short);
};
} // namespace Presonus
namespace presonus::panel {
// Independent observation of the last initialized diagnostic buffer. It never
// substitutes a Core type or establishes original local-variable layout/ABI.
// Null until an R/subcode1 message initializes the original function-local
// storage. Caller must respect its128-byte C-string bound/single-thread domain.
char *uartDiagnosticBuffer();
} // namespace presonus::panel
