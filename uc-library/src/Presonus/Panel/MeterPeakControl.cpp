#include "presonus/panel/meter_peak_control.hpp"

namespace Presonus::Panel {
MeterPeakControl::MeterPeakControl(int tag) : Control(tag) {}
MeterPeakControl::~MeterPeakControl() = default;

void *MeterPeakControl::castTo(int type) {
  if (type == 0x5043746c || type == 0x4d43746c)
    return this;
  return Control::castTo(type);
}
} // namespace Presonus::Panel
