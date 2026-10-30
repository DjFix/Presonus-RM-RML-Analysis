#pragma once

namespace Presonus::Panel {
// Portable source reconstruction. Observed ARM storage is count, 16 gains,
// 16 dB thresholds and two dB bounds; this does not establish original headers
// or a general binary ABI contract. setup requires count <= 16 when positive.
class DbTable {
public:
  DbTable(const float *decibels, int count);
  void setup(const float *decibels, int count);
  void setDbRange(float minimum, float maximum);
  int getCount() const;
  int getStepFromGain(float gain) const;
  int getStepFromNormalizedDB(float normalized) const;

private:
  int count_;
  float gains_[16];
  float decibels_[16];
  float minimum_;
  float maximum_;
};
} // namespace Presonus::Panel
