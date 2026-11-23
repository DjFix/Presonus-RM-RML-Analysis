#include "presonus/MeterBallistics.hpp"

#include <cmath>

namespace Presonus {
MeterBallistics::MeterDecayTable::MeterDecayTable(const float *breakpoints) {
  constexpr float minimumDb = -144.0f;
  constexpr float minimumAmplitude = 0x1.0efe7ep-24f;
  constexpr float decibelsToExponent = 0.05f;
  const float finalInterval = breakpoints[5] - breakpoints[4];
  for (std::size_t index = 0; index < entries_.size(); ++index) {
    const float upper = breakpoints[index + 1];
    entries_[index].amplitude =
        upper < minimumDb ? minimumAmplitude
                          : std::pow(10.0f, upper * decibelsToExponent);
    const float interval = upper - breakpoints[index];
    entries_[index].normalizedInterval = interval / finalInterval;
  }
}

MeterBallistics::MeterBallistics() {
  static constexpr float breakpoints[] = {-72.f, -45.f, -20.f, -6.f, -2.f, 0.f};
  static const MeterDecayTable table(breakpoints);
  decayTable_ = &table;
}

MeterBallistics::~MeterBallistics() = default;

float MeterBallistics::getPeakHold() const { return state_.peakHold; }

void MeterBallistics::reset() {
  state_.amplitude = 0.f;
  state_.peakHold = 0.f;
  state_.auxiliary.fill(0);
}

float MeterBallistics::getDecayDelta() const {
  if (decayTable_) {
    for (const auto &entry : decayTable_->entries()) {
      if (state_.amplitude < entry.amplitude)
        return state_.decayRate * (state_.amplitude * entry.normalizedInterval);
    }
  }
  return state_.decayRate;
}

float MeterBallistics::getPeakDecayDelta() const {
  constexpr float peakDecayRate = 0.06f;
  if (decayTable_) {
    for (const auto &entry : decayTable_->entries()) {
      if (state_.peakHold < entry.amplitude)
        return (state_.peakHold * entry.normalizedInterval) * peakDecayRate;
    }
  }
  return peakDecayRate;
}
} // namespace Presonus
