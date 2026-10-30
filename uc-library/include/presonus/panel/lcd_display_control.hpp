#pragma once
#include "presonus/panel/control.hpp"
namespace presonus::panel {
struct LCDDisplaySourcePort {};
} // namespace presonus::panel
namespace Presonus::Panel {
// Actual original Control base; independent construction and logical storage.
class LCDDisplayControl : public Control {
public:
  LCDDisplayControl(presonus::panel::LCDDisplaySourcePort, int tag,
                    unsigned display)
      : Control(tag), display_(display) {}
  // Ordinary original return spellings remain provisional/unencoded.
  void setValue(int);
  void transmit() override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void *castTo(int) override;

private:
  unsigned display_;
};
} // namespace Presonus::Panel
