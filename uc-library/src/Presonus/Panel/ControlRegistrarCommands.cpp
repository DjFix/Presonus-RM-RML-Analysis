#include "presonus/surface_panel/ControlHelpers.hpp"
namespace Presonus::Panel {
void ControlRegistrar::writeDualMsg(Uart_Msg_Type &message) {
  if (auto *port = getPort())
    port->writeMsg(message);
}
void ControlRegistrar::setAllLeds(bool enabled) {
  Uart_Msg_Type message{{0x4c, 0x0f, 0xff, static_cast<std::uint8_t>(enabled)}};
  writeDualMsg(message);
}
void ControlRegistrar::setAllMeters(bool enabled) {
  Uart_Msg_Type message{
      {0x56, 0xff, static_cast<std::uint8_t>(enabled ? 0x10 : 0), 0}};
  writeDualMsg(message);
}
void ControlRegistrar::scanSurface() {
  Uart_Msg_Type message{{0x67, 0x05, 0, 0}};
  writeDualMsg(message);
}
} // namespace Presonus::Panel
