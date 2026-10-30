#include "presonus/surface_panel/LEDState.hpp"

namespace Presonus::Panel {
void LEDControl::setmatchvalue(int value) { match_ = value; }

void LEDControl::setBlinkMode(BlinkMode mode) {
  const int requested = static_cast<int>(mode);
  if (blink_ == requested)
    return;
  blink_ = requested;
  if (requested == 3)
    broadcastValue(2);
  else if (auto *parameter = getParameter())
    paramChanged(parameter, 3);
}

void LEDControl::setColor(RGBLedColors color) {
  const int requested = static_cast<int>(color);
  if (color_ == requested)
    return;
  color_ = requested;
  dirty_ = 1;
  transmit();
}

void LEDControl::setFullOff() { broadcastValue(3); }

void LEDControl::broadcastValue(int value) {
  if (presonus::panel::ControlAccess::lastLevel(*this) == value)
    return;
  presonus::panel::ControlAccess::lastLevel(*this) = value;
  transmit();
}
} // namespace Presonus::Panel
