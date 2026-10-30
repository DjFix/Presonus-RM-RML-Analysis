#include "presonus/panel/phantom_power_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace Presonus::Panel {
void PhantomPowerControl::broadcastValue(int value) {
  auto &last = presonus::panel::ControlAccess::lastLevel(*this);
  if (last != value) {
    last = value;
    transmit();
  }
}
void PhantomPowerControl::transmit() {
  if (disabled_)
    return;
  auto *io = presonus::panel::ControlAccess::io(*this);
  if (!io)
    return;
  Uart_Msg_Type message{};
  message.bytes[0] = 'M';
  message.bytes[1] =
      static_cast<unsigned char>(presonus::panel::ControlAccess::tag(*this));
  message.bytes[2] = static_cast<unsigned char>(
      presonus::panel::ControlAccess::lastLevel(*this));
  io->writeMsg(message);
}
void PhantomPowerControl::disableControl(bool disabled, bool) {
  disabled_ = disabled;
  if (!disabled)
    transmit();
}
void PhantomPowerControl::paramChanged(Core::Portable::Parameter *p,
                                       int message) {
  Control::paramChanged(p, message);
  if (message == Core::Portable::Parameter::kChanged) {
    const float scaled = p->getNormalized() * 255.f;
    if (!std::isfinite(scaled) ||
        static_cast<double>(scaled) < std::numeric_limits<int>::min() ||
        static_cast<double>(scaled) > std::numeric_limits<int>::max())
      throw std::domain_error(
          "phantom normalized value outside portable int domain");
    broadcastValue(static_cast<int>(scaled));
  }
}
} // namespace Presonus::Panel
