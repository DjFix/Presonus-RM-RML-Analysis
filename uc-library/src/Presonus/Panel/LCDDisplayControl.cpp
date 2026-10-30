#include "presonus/panel/lcd_display_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cmath>
#include <stdexcept>
namespace Presonus::Panel {
void LCDDisplayControl::setValue(int value) {
  auto &last = presonus::panel::ControlAccess::lastLevel(*this);
  if (last != value) {
    last = value;
    transmit();
  }
}
void LCDDisplayControl::transmit() {
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  if (dispatch.disabled) {
    auto &queue = dispatch.dirty;
    for (int i = 0; i < queue.count(); ++i)
      if (queue.at(i) == this)
        return;
    if (queue.count() < queue.getCapacity() || queue.resize(queue.count() + 1))
      queue.add(this);
    return;
  }
  if (auto *io = presonus::panel::ControlAccess::io(*this)) {
    const auto value =
        static_cast<unsigned>(presonus::panel::ControlAccess::lastLevel(*this));
    Uart_Msg_Type message{{'b', static_cast<unsigned char>(display_),
                           static_cast<unsigned char>(value),
                           static_cast<unsigned char>(value >> 8)}};
    io->writeMsg(message);
  }
}
void LCDDisplayControl::paramChanged(Core::Portable::Parameter *p,
                                     int message) {
  Control::paramChanged(p, message);
  if (message == Core::Portable::Parameter::kChanged) {
    const float value = p->getValue();
    if (!std::isfinite(value) || value < -2147483648.f || value >= 2147483648.f)
      throw std::domain_error("finite LCD value in int32 domain required");
    setValue(static_cast<int>(value));
  }
}
void *LCDDisplayControl::castTo(int type) {
  return type == 0x4c434443 ? this : Control::castTo(type);
}
} // namespace Presonus::Panel
