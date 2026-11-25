#include "presonus/panel/meter_level_control.hpp"

namespace Presonus::Panel {

MeterLevelControl::MeterLevelControl(int tag) : MeterControl(tag) {}

MeterLevelControl::~MeterLevelControl() = default;

void *MeterLevelControl::castTo(int type) {
  constexpr int meterLevelControl = 0x4d4c436c;
  if (type == meterLevelControl)
    return this;
  return MeterControl::castTo(type);
}

int MeterLevelControl::getParameterMode() const { return parameterMode_; }

} // namespace Presonus::Panel
