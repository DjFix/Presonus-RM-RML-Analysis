#include "core/public/corestringbuffer.h"
#include "presonus/panel/uart_message_handler.hpp"
#include <cstring>

namespace {
char *diagnosticBuffer = nullptr; // Independent state-observation bridge only.
unsigned short value(const Uart_Msg_Type &message) {
  return static_cast<unsigned short>(message.bytes[2]) |
         (static_cast<unsigned short>(message.bytes[3]) << 8);
}
int signedValue(const Uart_Msg_Type &message) {
  const auto word = value(message);
  return word < 0x8000 ? word : static_cast<int>(word) - 0x10000;
}
} // namespace
namespace presonus::panel {
char *uartDiagnosticBuffer() { return diagnosticBuffer; }
} // namespace presonus::panel
namespace Presonus {
void *UARTMessageHandler::castTo(Core::Portable::TypedObject::TypeID tag) {
  return tag == 0x75617274 ? this : nullptr; // Original literal type ID "uart".
}
UARTMessageHandler::~UARTMessageHandler() = default;

void UARTMessageHandler::processMsg(Uart_Msg_Type &message, int port) {
  const auto &v = message.bytes;
  switch (v[0]) {
  case 'G':
    handleGlobalResponse(port, message);
    break;
  case 'H':
    handleFaderSensitivity(v[1]);
    break;
  case 'K':
    handleKeyValue(v[1], value(message));
    break;
  case 'P':
    handleCalibrateTouchscreenProgress(v[1], v[2]);
    break;
  case 'R':
    if (v[1] == 0) {
      handleError(port, value(message));
    } else if (v[1] == 1) {
      // Actual CCL source supplies matching lazy first-byte initialization and
      // bounded append semantics. Original local static type/guard layout is
      // unresolved; retain its original variable identity, not an ABI claim.
      static Core::CString128 panelMessage;
      diagnosticBuffer = panelMessage.getBuffer();
      panelMessage.append(static_cast<char>(value(message)));
      if (value(message) == 10)
        panelMessage.empty();
    }
    break;
  case 'S':
    handleSwitch(v[2], v[1], false);
    break;
  case 'T':
  case 'U':
  case 'z':
    handleTouchscreen(reinterpret_cast<Touchscreen_Type &>(message));
    break;
  case 'e':
    handleEncoder(v[1], signedValue(message));
    break;
  case 'f':
    handleFader(v[1], value(message));
    break;
  case 'h':
    handleLineSense(v[1], v[2], v[3]);
    break;
  case 'j':
    handleMovingFaderMcuStatus(v[1], v[2], v[3]);
    break;
  case 'm':
    handleFaderStatus(v[1], v[2]);
    break;
  case 'p':
    handlePot(v[1], value(message));
    break;
  case 's':
    handleSwitch(v[2], v[1], true);
    break;
  case 't':
    handleTemperature(v[1], value(message));
    break;
  case 'v':
    handleFaderSpeed(v[1]);
    break;
  default:
    break;
  }
}

// Actual original 16-byte no-op virtual defaults, each separately byte-checked
// in both input ELFs. They deliberately neither return a fabricated success
// value nor mutate message/state. Return declarations remain pending.
void UARTMessageHandler::handleSwitch(int, int, bool) {}
void UARTMessageHandler::handleFader(int, int) {}
void UARTMessageHandler::handleFaderStatus(int, unsigned char) {}
void UARTMessageHandler::handlePot(int, int) {}
void UARTMessageHandler::handleEncoder(int, int) {}
void UARTMessageHandler::handleTemperature(int, int) {}
void UARTMessageHandler::handleVersion(int, Uart_Msg_Type &) {}
void UARTMessageHandler::handleError(int, unsigned short) {}
void UARTMessageHandler::handleTouchscreen(Touchscreen_Type &) {}
void UARTMessageHandler::handleMovingFaderMcuStatus(unsigned char,
                                                    unsigned char,
                                                    unsigned char) {}
void UARTMessageHandler::handleGlobalResponse(int, Uart_Msg_Type &) {}
void UARTMessageHandler::handleCalibrateTouchscreenProgress(unsigned char,
                                                            unsigned short) {}
void UARTMessageHandler::handleKeyValue(unsigned char, unsigned short) {}
void UARTMessageHandler::handleLineSense(int, int, int) {}
void UARTMessageHandler::handleFaderSensitivity(unsigned short) {}
void UARTMessageHandler::handleFaderSpeed(unsigned short) {}
} // namespace Presonus
