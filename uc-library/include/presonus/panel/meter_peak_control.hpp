#pragma once
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/DbTable.hpp"

namespace presonus::panel {
struct MeterPeakControlAccess;
}

namespace Presonus::Panel {
class MeterPeakControl : public Control {
public:
  explicit MeterPeakControl(int);
  ~MeterPeakControl() override;
  void *castTo(int) override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void broadcastValue(int) override;
  void transmit() override;

private:
  // Portable state inferred from value adjustment and table selection reads.
  int peakOffset_ = 0;
  const DbTable *scaleTable_ = nullptr;
  int scaleMode_ = 0;

  friend struct presonus::panel::MeterPeakControlAccess;
};
} // namespace Presonus::Panel
