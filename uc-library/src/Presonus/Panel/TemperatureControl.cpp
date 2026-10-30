#include "presonus/panel/temperature_control.hpp"
namespace Presonus::Panel {
void TemperatureControl::receiveValue(int value) {
  if (auto *p = presonus::panel::ControlAccess::parameter(*this))
    p->setNormalized(static_cast<float>(value) * 0x1p-10f, true);
}
void *TemperatureControl::castTo(int type) {
  return type == 0x54656d43 ? this : Control::castTo(type);
}
} // namespace Presonus::Panel
