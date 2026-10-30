#pragma once
#include "presonus/panel/switch_control.hpp"
namespace presonus::panel {
struct BlinkLEDAccess;
}
namespace Presonus::Panel {
// Original RTTI proves SwitchControl base. Source fields are portable state,
// not ARM object-layout declarations. Ordinary returns remain unencoded.
class BlinkLEDControl : public SwitchControl {
public:
  BlinkLEDControl(int, int, bool);
  ~BlinkLEDControl() override;
  void *castTo(int) override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void transmitBlinkRate(float);

private:
  unsigned char resynchronize_ = 0;
  friend struct presonus::panel::BlinkLEDAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
struct BlinkLEDAccess {
  static auto &resynchronize(Presonus::Panel::BlinkLEDControl &v) {
    return v.resynchronize_;
  }
};
} // namespace presonus::panel
