#pragma once
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/InputPin.hpp"
namespace presonus::panel {
struct InputGPIOAccess;
}
namespace Presonus::Panel {
// Original RTTI: Control primary base, PinStateObserver secondary. Source-port
// state/offsets are independent; no ARM class-layout claim.
class InputGPIOControl : public Control, public PinStateObserver {
public:
  InputGPIOControl(int, int, bool, bool);
  ~InputGPIOControl() override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void pinStateChanged(int, int) override;
  void switchDown();
  void switchUp();

private:
  InputPin pin_;
  bool completeOnDown_;
  bool inverse_;
  friend struct presonus::panel::InputGPIOAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
struct InputGPIOAccess {
  static auto &pin(Presonus::Panel::InputGPIOControl &v) { return v.pin_; }
};
} // namespace presonus::panel
