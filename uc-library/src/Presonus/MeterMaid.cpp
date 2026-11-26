#include "presonus/MeterMaid.hpp"

#include "core/portable/coreparams.h"

namespace Presonus {
MeterMaid::MeterMaid() = default;
MeterMaid::MeterMaid(DecayTablePolicy policy) : MeterBallistics(policy) {}
MeterMaid::~MeterMaid() = default;

void MeterMaid::bindParameters(Core::Portable::NumericParam *meter,
                               Core::Portable::NumericParam *peak) noexcept {
  meter_ = meter;
  peak_ = peak;
}

void MeterMaid::bindIndicatorParameters(
    Core::Portable::NumericParam *signal,
    Core::Portable::NumericParam *clip) noexcept {
  signal_ = signal;
  clip_ = clip;
}

void MeterMaid::setMeter(float value) {
  if (meter_)
    meter_->setValue(value, false);
}

void MeterMaid::setPeak(float value) {
  if (peak_)
    peak_->setValue(value, false);
}
void MeterMaid::setSignal(bool present) {
  if (signal_)
    signal_->setValue(static_cast<float>(present), false);
}

void MeterMaid::setClipped(bool clipped) {
  if (clip_)
    clip_->setValue(static_cast<float>(clipped), false);
}

bool MeterMaid::isClipped() const { return clip_ && clip_->getValue() > 0.f; }
} // namespace Presonus
