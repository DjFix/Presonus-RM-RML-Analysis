#include "presonus/surface_panel/MeterControl.hpp"

namespace Presonus::Panel {
// These initializers provide portable storage, not recovered startup behavior.
int MeterControl::numMeterSteps[2] = {16, 16};
DbTable MeterControl::inputTable(nullptr, 0);
DbTable MeterControl::outputTable(nullptr, 0);

void MeterControl::setDbRange(float minimum, float maximum) {
  inputTable.setDbRange(minimum, maximum);
  outputTable.setDbRange(minimum, maximum);
}

void MeterControl::setMeterSteps(int inputCount, int outputCount,
                                 const float *inputSteps,
                                 const float *outputSteps) {
  numMeterSteps[0] = inputCount;
  numMeterSteps[1] = outputCount;
  inputTable.setup(inputSteps, inputCount);
  outputTable.setup(outputSteps, outputCount);
}

int MeterControl::getNumMeterSteps(BusDirection direction, bool) const {
  if (overrideCount_ != nullptr)
    return *overrideCount_;
  const int index = static_cast<int>(direction);
  // Original guard is signed <= 1. The fallback's negative-index domain is
  // undefined/outside this portable port; callers must supply index >= 0.
  return index <= 1 ? numMeterSteps[index] : 0;
}

void MeterControl::setBusDirection(BusDirection direction) {
  if (static_cast<int>(direction) <= 1)
    direction_ = static_cast<int>(direction);
}
} // namespace Presonus::Panel
