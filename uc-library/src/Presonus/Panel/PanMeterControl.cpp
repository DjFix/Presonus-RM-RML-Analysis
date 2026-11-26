#include "presonus/panel/pan_meter_control.hpp"

namespace Presonus::Panel {

PanMeterControl::PanMeterControl(int tag) : MeterLevelControl(tag) {}

PanMeterControl::~PanMeterControl() = default;

void *PanMeterControl::castTo(int type) {
  constexpr int panMeterControlId = 0x50616e43;
  if (type == panMeterControlId)
    return this;
  return MeterLevelControl::castTo(type);
}

} // namespace Presonus::Panel
