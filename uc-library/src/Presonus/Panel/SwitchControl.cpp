#include "presonus/panel/switch_control.hpp"

namespace Presonus::Panel {
SwitchControl::SwitchControl(int tag, int index, bool immediate)
    : LEDControl(tag, index, -1), pressed_(0), immediate_(immediate),
      disabled_(0), receiver_(nullptr), held_(0) {}

SwitchControl::~SwitchControl() {
  if (receiver_)
    receiver_->detach(receiver_->context, *this);
}

void *SwitchControl::castTo(int type) {
  return type == 0x53776943 || type == 0x4c656443 || type == 0x4374726c
             ? this
             : nullptr;
}
std::uint8_t SwitchControl::isImmediate() const { return immediate_; }
void SwitchControl::setImmediate(bool immediate) { immediate_ = immediate; }

void SwitchControl::disableControl(bool disabled, bool reset) {
  auto *parameter = getParameter();
  disabled_ = disabled;
  if (parameter && disabled && reset)
    presonus::panel_binding::resetSwitchParameter(*parameter);
}
} // namespace Presonus::Panel
