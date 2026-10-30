#include "presonus/panel/blink_led_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cmath>
#include <stdexcept>
namespace Presonus::Panel {
BlinkLEDControl::BlinkLEDControl(int tag, int group, bool immediate)
    : SwitchControl(tag, group, immediate) {}
BlinkLEDControl::~BlinkLEDControl() = default;
void *BlinkLEDControl::castTo(int tag) {
  return tag == 0x426c6e6b ? this : SwitchControl::castTo(tag);
}
void BlinkLEDControl::paramChanged(Core::Portable::Parameter *parameter,
                                   int message) {
  if (presonus::panel::ControlAccess::lastLevel(*this) != 4 &&
      getParameter() == parameter)
    LEDControl::paramChanged(parameter, message);
  if (message != 3)
    return;
  if (getTertiaryParameter() == parameter)
    resynchronize_ = 1;
  if (getAltParameter() != parameter)
    return;
  // Preserve three real reads on the blinking branch; providers may expose
  // distinct successive values. The first two reads occur before comparison.
  const float first = parameter->getValue();
  const float second = parameter->getValue();
  if (first > 0.08f) {
    broadcastValue(4);
    transmitBlinkRate(parameter->getValue());
  } else {
    broadcastValue(second == 0.0f ? 0 : 1);
  }
}
void BlinkLEDControl::transmitBlinkRate(float seconds) {
  const float milliseconds = seconds * 1000.0f;
  // Bounded portable domain. Original compiler conversion for negative,
  // nonfinite and out-of-uint32 inputs remains explicit pending work.
  if (!std::isfinite(milliseconds) || milliseconds < 0.0f ||
      milliseconds >= 4294967296.0f)
    throw std::domain_error(
        "finite nonnegative in-range blink duration required");
  const auto duration = static_cast<unsigned>(milliseconds) & 0xffffU;
  const auto pulse = duration <= 130 ? (duration - 80U) & 0xffU : 50U;
  auto remainder = (duration - pulse) & 0xffffU;
  if (resynchronize_)
    remainder |= 0x8000U;
  resynchronize_ = 0;
  Uart_Msg_Type message{{0x42, static_cast<unsigned char>(pulse),
                         static_cast<unsigned char>(remainder),
                         static_cast<unsigned char>(remainder >> 8)}};
  // Original dereferences IO unconditionally; a live binding is required.
  presonus::panel::ControlAccess::io(*this)->writeMsg(message);
}
} // namespace Presonus::Panel
