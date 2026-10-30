#pragma once
#include "presonus/panel/control.hpp"
namespace presonus::panel {
struct PhantomSourcePort {};
struct PhantomAccess;
} // namespace presonus::panel
namespace Presonus::Panel {
// Actual original Control base; independent constructor and logical storage.
// No original lifecycle/layout/ARM ABI claim. Ordinary void returns
// provisional.
class PhantomPowerControl : public Control {
public:
  PhantomPowerControl(presonus::panel::PhantomSourcePort, int tag)
      : Control(tag), disabled_(false) {}
  void broadcastValue(int) override;
  void transmit() override;
  void disableControl(bool, bool) override;
  void paramChanged(Core::Portable::Parameter *, int) override;

private:
  bool disabled_;
  friend struct presonus::panel::PhantomAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
struct PhantomAccess {
  static bool disabled(const Presonus::Panel::PhantomPowerControl &v) {
    return v.disabled_;
  }
};
} // namespace presonus::panel
