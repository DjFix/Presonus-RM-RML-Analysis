#pragma once

#include "presonus/panel/meter_level_control.hpp"

namespace Presonus::Panel {

class PanMeterControl : public MeterLevelControl {
public:
  explicit PanMeterControl(int tag);
  ~PanMeterControl() override;
  void *castTo(int type) override;
};

} // namespace Presonus::Panel
