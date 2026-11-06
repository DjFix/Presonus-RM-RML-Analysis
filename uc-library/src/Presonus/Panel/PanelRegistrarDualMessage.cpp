#include "presonus/panel/PanelRegistrar.hpp"
namespace Presonus::Panel {
void PanelRegistrar::writeDualMsg(Uart_Msg_Type &message) {
  ControlRegistrar::writeDualMsg(message);
  // Deliberately read the live state after primary dispatch: synchronous
  // writes may change both the message and the enabled/secondary selection.
  if (state_.secondaryEnabled) {
    if (!state_.secondaryPort)
      throw std::logic_error("PanelRegistrar enabled secondary port is null");
    state_.secondaryPort->writeMsg(message);
  }
}
} // namespace Presonus::Panel
