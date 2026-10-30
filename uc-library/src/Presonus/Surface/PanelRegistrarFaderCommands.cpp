#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

namespace Presonus::Surface {
void PanelRegistrar::sendFaderFunctionMessage(unsigned char function) {
  Uart_Msg_Type message{{0x67, 0x0e, function, 0}};
  // Original virtual writeDualMsg selects getPort(), skips a null port, and
  // calls that actual port's writeMsg once. Its return value is ignored.
  // This independent borrowed selection does not assert registrar inheritance
  // or private layout, and is reread for each command.
  if (commandState_ && commandState_->port)
    commandState_->port->writeMsg(message);
}
void PanelRegistrar::requestUpdatedFaderParameters() {
  sendFaderFunctionMessage(1);
  sendFaderFunctionMessage(2);
}
void PanelRegistrar::invokeFaderCalibration(bool enabled) {
  if (enabled)
    sendFaderFunctionMessage(0);
}
} // namespace Presonus::Surface
