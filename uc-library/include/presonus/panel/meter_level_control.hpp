#pragma once

#include "presonus/surface_panel/MeterControl.hpp"

namespace presonus::panel {
struct MeterLevelControlAccess;
}

namespace Presonus::Panel {

// Portable lifecycle, cast and mode read. Meter output and parameter-mode
// mutation remain outside this recovered interface.
class MeterLevelControl : public MeterControl {
public:
  explicit MeterLevelControl(int tag);
  ~MeterLevelControl() override;
  void *castTo(int type) override;
  int getParameterMode() const override;

private:
  int parameterMode_ = 0;
  bool clipActive_ = false;
  friend struct presonus::panel::MeterLevelControlAccess;
};

} // namespace Presonus::Panel

namespace presonus::panel {

// Typed state access for offline source-port validation.
struct MeterLevelControlAccess {
  static auto &parameterMode(Presonus::Panel::MeterLevelControl &v) {
    return v.parameterMode_;
  }
  static auto &clipActive(Presonus::Panel::MeterLevelControl &v) {
    return v.clipActive_;
  }
};

} // namespace presonus::panel
