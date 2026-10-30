#pragma once
#include "presonus/panel/pot_fader_control.hpp"
namespace presonus::panel {
struct MotorizedFaderAccess;
}
namespace Presonus::Panel {
class MotorizedFaderControl : public FaderControl {
public:
  explicit MotorizedFaderControl(int);
  ~MotorizedFaderControl() override;
  void *castTo(int) override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void broadcastValue(int) override;
  void transmit() override;
  void receiveValue(int) override;
  void handleTouch(bool);

private:
  // Independent app state, not original field declarations/layout/ARM ABI.
  unsigned char receiving_ = 0, touched_ = 0;
  int lastInput_ = 0;
  friend struct presonus::panel::MotorizedFaderAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
// Independent shared source-port deferred storage, not a renamed ELF global.
Core::Vector<Presonus::Panel::Control *> &motorizedDeferredControls();
struct MotorizedFaderAccess {
  static auto &receiving(Presonus::Panel::MotorizedFaderControl &v) {
    return v.receiving_;
  }
  static auto &touched(Presonus::Panel::MotorizedFaderControl &v) {
    return v.touched_;
  }
  static auto &lastInput(Presonus::Panel::MotorizedFaderControl &v) {
    return v.lastInput_;
  }
};
} // namespace presonus::panel
