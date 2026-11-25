#pragma once
#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/DbTable.hpp"

namespace presonus::surface_panel_port {
struct MeterControlAccess;
}

namespace Presonus::Panel {
// Portable source model with Control lifecycle and independent meter storage.
// The enum's original enumerator names/underlying declaration remain unknown.
class MeterControl : public Control {
public:
  MeterControl();
  explicit MeterControl(int tag);
  ~MeterControl() override;

  enum BusDirection : int {};
  static void setDbRange(float minimum, float maximum);
  static void setMeterSteps(int inputCount, int outputCount,
                            const float *inputSteps, const float *outputSteps);
  int getNumMeterSteps(BusDirection direction, bool alternate) const;
  void setBusDirection(BusDirection direction);
  // Portable declaration for the observed receiver-or-null result.
  void *castTo(int classId) override;

private:
  friend struct presonus::surface_panel_port::MeterControlAccess;
  static int numMeterSteps[2];
  static DbTable inputTable;
  static DbTable outputTable;
  // Only pointer-nullness and dereferenced first int are established at +0x20.
  // This portable representation does not invent the historical pointee type.
  const int *overrideCount_ = nullptr;
  int direction_ = 0;
};
} // namespace Presonus::Panel

namespace presonus::surface_panel_port {
// Independent port/testing access; none of these helpers are original methods.
struct MeterControlAccess {
  static void setState(Presonus::Panel::MeterControl &control,
                       const int *overrideCount, int direction) {
    control.overrideCount_ = overrideCount;
    control.direction_ = direction;
  }
  static int direction(const Presonus::Panel::MeterControl &control) {
    return control.direction_;
  }
  static const int *
  overrideCount(const Presonus::Panel::MeterControl &control) {
    return control.overrideCount_;
  }
  static int *counts() { return Presonus::Panel::MeterControl::numMeterSteps; }
  static Presonus::Panel::DbTable &input() {
    return Presonus::Panel::MeterControl::inputTable;
  }
  static Presonus::Panel::DbTable &output() {
    return Presonus::Panel::MeterControl::outputTable;
  }
};
} // namespace presonus::surface_panel_port
