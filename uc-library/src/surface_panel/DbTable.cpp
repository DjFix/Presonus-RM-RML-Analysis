#include "presonus/surface_panel/DbTable.hpp"
#include <cmath>

namespace Presonus::Panel {
DbTable::DbTable(const float *decibels, int count)
    : count_(0), minimum_(-144.0F), maximum_(0.0F) {
  setup(decibels, count);
}

void DbTable::setup(const float *decibels, int count) {
  count_ = count;
  for (int index = 0; index < count_; ++index) {
    const float db = decibels[index];
    gains_[index] = db < -144.0F ? 0x1.0efe7ep-24F : ::powf(10.0F, db * 0.05F);
    decibels_[index] = db;
  }
}

void DbTable::setDbRange(float minimum, float maximum) {
  minimum_ = minimum;
  maximum_ = maximum;
}

int DbTable::getCount() const { return count_; }

int DbTable::getStepFromGain(float gain) const {
  if (count_ <= 0 || gain < gains_[0])
    return 0;
  int step = 1;
  for (; step < count_; ++step)
    if (gains_[step] > gain)
      break;
  return step;
}

int DbTable::getStepFromNormalizedDB(float normalized) const {
  if (count_ <= 0)
    return 0;
  const float span = maximum_ - minimum_;
  const float scaled = normalized * span;
  const float db = minimum_ + scaled;
  if (db < decibels_[0])
    return 0;
  int step = 1;
  for (; step < count_; ++step)
    if (db < decibels_[step])
      break;
  return step;
}
} // namespace Presonus::Panel
