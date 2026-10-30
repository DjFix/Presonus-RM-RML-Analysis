#include "core/system/coredebug.h"
#include "presonus/panel/input_gpio_control.hpp"
namespace Presonus::Panel {
InputGPIOControl::InputGPIOControl(int tag, int pin, bool completeOnDown,
                                   bool inverse)
    : Control(tag), pin_(-1, nullptr), completeOnDown_(completeOnDown),
      inverse_(inverse) {
  pin_.setup(pin, this);
  pin_.read_debounce();
}
InputGPIOControl::~InputGPIOControl() = default;
void InputGPIOControl::paramChanged(Core::Portable::Parameter *parameter,
                                    int message) {
  if (message != 5)
    return;
  if (getParameter() == parameter)
    presonus::panel::ControlAccess::parameter(*this) = nullptr;
  parameter->removeObserver(this);
}
void InputGPIOControl::pinStateChanged(int, int value) {
  bool pressed = value != 0;
  if (inverse_)
    pressed = !pressed;
  if (pressed)
    switchDown();
  else
    switchUp();
}
void InputGPIOControl::switchDown() {
  Core::DebugPrintf("GPIO switchDown\n");
  if (!getParameter())
    return;
  getParameter()->beginEdit();
  auto *parameter = getParameter();
  if (parameter->getType() == Core::Portable::ParamInfo::kToggle) {
    parameter->setValue(parameter->getValue() == 1.f ? 0.f : 1.f, true);
  } else {
    const float value = parameter->getValue();
    const float maximum = getParameter()->getMax();
    if (value == maximum)
      getParameter()->setValue(0.f, true);
    else {
      parameter = getParameter();
      parameter->setValue(parameter->getValue() + 1.f, true);
    }
  }
  if (completeOnDown_)
    getParameter()->endEdit();
}
void InputGPIOControl::switchUp() {
  Core::DebugPrintf("GPIO switchUp\n");
  if (auto *parameter = getParameter(); parameter && !completeOnDown_)
    parameter->endEdit();
}
} // namespace Presonus::Panel
