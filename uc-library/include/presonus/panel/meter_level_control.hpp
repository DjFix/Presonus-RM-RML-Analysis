#pragma once

#include "presonus/surface_panel/MeterControl.hpp"

namespace presonus::panel {
struct MeterLevelControlAccess;
}

namespace Presonus::Panel {

// Portable source port. Ordinary returns, storage and ARM ABI remain
// provisional.
class MeterLevelControl : public MeterControl {
public:
  explicit MeterLevelControl(int tag);
  ~MeterLevelControl() override;
  void *castTo(int type) override;
  int getParameterMode() const override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  bool setParameter(Core::Portable::Parameter *, int) override;
  bool setClipParameter(Core::Portable::Parameter *);
  void broadcastValue(int) override;
  void transmit() override;
  int getNumMeterSteps(bool alternate) const;

private:
  int parameterMode_ = 0;
  bool clipActive_ = false;
  int transmittedMode_ = 0;
  bool blank_ = false;
  int levelOffset_ = 0;
  // Explicit portable typed custom-table binding; no pointer-layout inference.
  const DbTable *customTable_ = nullptr;
  friend struct presonus::panel::MeterLevelControlAccess;
};

} // namespace Presonus::Panel

namespace presonus::panel {

// Typed state access for offline source-port validation.
struct MeterLevelControlAccess {
  static auto &parameterMode(Presonus::Panel::MeterLevelControl &v) {
    return v.parameterMode_;
  }
  static auto &customTable(Presonus::Panel::MeterLevelControl &v) {
    return v.customTable_;
  }
  static auto &offset(Presonus::Panel::MeterLevelControl &v) {
    return v.levelOffset_;
  }
  static auto &transmittedMode(Presonus::Panel::MeterLevelControl &v) {
    return v.transmittedMode_;
  }
  static auto &blank(Presonus::Panel::MeterLevelControl &v) { return v.blank_; }
  static auto &clipActive(Presonus::Panel::MeterLevelControl &v) {
    return v.clipActive_;
  }
};

} // namespace presonus::panel
