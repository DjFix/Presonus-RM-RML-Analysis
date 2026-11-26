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

MeterBallistics::MeterBallistics(DecayTablePolicy policy) : MeterBallistics() {
  if (policy == DecayTablePolicy::None)
    decayTable_ = nullptr;
}

MeterBallistics::~MeterBallistics() = default;

bool MeterBallistics::isClipped() const { return effects_.clipped; }
void MeterBallistics::setClipped(bool value) { effects_.clipped = value; }
void MeterBallistics::setSignal(bool value) { effects_.signal = value; }
void MeterBallistics::setMeter(float value) { effects_.meter = value; }
void MeterBallistics::setPeak(float value) { effects_.peak = value; }

float MeterBallistics::setLevel(float value) {
  if (state_.amplitude < value)
    state_.auxiliary[3] = 0;
  return idleSetLevel(value);
}

float MeterBallistics::idleSetLevel(float value) {
  if (value > 1.f)
    value = 1.f;
  // ARM compares this counter as a signed word and increments modulo 2^32.
  auto &delay = state_.auxiliary[3];
  if (delay > 4 && delay < 0x80000000u)
    state_.amplitude -= getDecayDelta();
  ++delay;
  if (state_.amplitude < 0.f)
    state_.amplitude = 0.f;

  auto &hold = state_.auxiliary[0];
  if (hold < 0x80000000u)
    --hold;
  else {
    state_.peakHold -= getPeakDecayDelta();
    if (state_.peakHold < 0.f)
      state_.peakHold = 0.f;
  }
  if (value > state_.amplitude)
    state_.amplitude = value;
  if (state_.peakHold < state_.amplitude) {
    state_.peakHold = state_.amplitude;
    hold = 80;
  }
  setMeter(state_.amplitude);
  setPeak(state_.active ? state_.peakHold : 0.f);

  auto &signal = state_.auxiliary[2];
  if (value > 0.0125f && !isClipped()) {
    signal = 10;
    setSignal(true);
  }
  if (signal != 0 && --signal == 0)
    setSignal(false);

  auto &clip = state_.auxiliary[1];
  if (value > 0.99f) {
    clip = 200;
    setClipped(true);
    setSignal(false);
  }
  if (clip != 0 && --clip == 0)
    setClipped(false);
  return state_.amplitude;
}

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
