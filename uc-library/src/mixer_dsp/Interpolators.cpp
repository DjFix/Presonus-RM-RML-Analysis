#include "presonus/mixer_dsp/Interpolators.hpp"
#include "Logarithm.hpp"

extern "C" float presonus_glibc29_expf(float);
namespace {
float add(float a, float b) {
  volatile float value = a + b;
  return value;
}
float subtract(float a, float b) {
  volatile float value = a - b;
  return value;
}
float multiply(float a, float b) {
  volatile float value = a * b;
  return value;
}
float divide(float a, float b) {
  volatile float value = a / b;
  return value;
}
} // namespace

namespace presonus::dsp::detail {
SourceZoomState::SourceZoomState() = default;
SourceZoomState::SourceZoomState(float low, float high, float power)
    : Core::ZoomInterpolator(low, high, power) {}
SourceZoomState::~SourceZoomState() = default;
void SourceZoomState::seedPortable(float low, float high, float power,
                                   float reciprocal) {
  Core::Interpolator::setRange(low, high, power);
  midRangeInv = reciprocal;
}
float SourceZoomState::portableReciprocal() const { return midRangeInv; }
} // namespace presonus::dsp::detail

namespace Presonus::Dsp {
using presonus::dsp::InterpolationPortTag;
using presonus::dsp::InterpolationState;
RatioInterpolator::RatioInterpolator(float minimum, float maximum)
    : Core::Interpolator(minimum, maximum, 1.f, nullptr),
      linear_(add(divide(-1.f, minimum), 1.f),
              add(divide(-1.f, maximum), 1.f)) {
  setRange(minimum, maximum, -1.f);
}
RatioInterpolator::RatioInterpolator(InterpolationPortTag,
                                     const InterpolationState &state)
    : Core::Interpolator(state[0], state[1], state[2]) {
  linear_.setRange(state[3], state[4], state[5]);
}
RatioInterpolator::~RatioInterpolator() = default;
void RatioInterpolator::setRange(float minimum, float maximum, float midpoint) {
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  linear_.setRange(add(divide(-1.f, minimum), 1.f),
                   add(divide(-1.f, maximum), 1.f), -1.f);
}
float RatioInterpolator::normalizedToRange(float value) const {
  const float linear = linear_.normalizedToRange(value);
  return linear < 1.f ? divide(1.f, subtract(1.f, linear)) : maxRange;
}
float RatioInterpolator::rangeToNormalized(float value) const {
  const float linear = value > 0.f ? add(divide(-1.f, value), 1.f) : 0.f;
  return linear_.rangeToNormalized(linear);
}
InterpolationState RatioInterpolator::portableState() const {
  return {minRange,
          maxRange,
          midRange,
          linear_.getMinRange(),
          linear_.getMaxRange(),
          linear_.getMidRange(),
          0,
          0};
}

ExpInterpolator::ExpInterpolator(float minimum, float maximum, float midpoint)
    : Core::Interpolator(0.f, 1.f, 1.f, nullptr), offset_(0.f), scale_(1.f),
      exponent_(1.f) {
  // Original constructor deliberately does not initialize either inverse.
  // setRange establishes them only for a nondegenerate asymmetric curve.
  setRange(minimum, maximum, midpoint);
}
ExpInterpolator::ExpInterpolator(InterpolationPortTag,
                                 const InterpolationState &state)
    : Core::Interpolator(state[0], state[1], state[2]), offset_(state[3]),
      scale_(state[4]), inverseScale_(state[5]), exponent_(state[6]),
      inverseExponent_(state[7]) {}
ExpInterpolator::~ExpInterpolator() = default;
void ExpInterpolator::setRange(float minimum, float maximum, float midpoint) {
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  const float span = subtract(maximum, minimum);
  if (!(span > 0.f))
    return;
  const float left = subtract(midpoint, minimum);
  if (!(left > 0.f))
    return;
  const float right = subtract(maximum, midpoint);
  if (!(right > 0.f) || right == left)
    return;
  const float ratio = divide(multiply(right, right), multiply(left, left));
  scale_ = divide(span, subtract(ratio, 1.f));
  exponent_ = presonus::dsp::detail::sourceLogf(ratio);
  offset_ = subtract(minimum, scale_);
  inverseScale_ = divide(1.f, scale_);
  inverseExponent_ = divide(1.f, exponent_);
}
float ExpInterpolator::normalizedToRange(float value) const {
  if (value < 0.f)
    value = 0.f;
  else if (!(value < 1.f))
    value = 1.f;
  const float exponential = presonus_glibc29_expf(multiply(value, exponent_));
  return add(offset_, multiply(scale_, exponential));
}
float ExpInterpolator::rangeToNormalized(float value) const {
  if (minRange > value)
    value = minRange;
  else if (!(value < maxRange))
    value = maxRange;
  const float scaled = multiply(subtract(value, offset_), inverseScale_);
  return multiply(inverseExponent_, presonus::dsp::detail::sourceLogf(scaled));
}
InterpolationState ExpInterpolator::portableState() const {
  return {minRange, maxRange,      midRange,  offset_,
          scale_,   inverseScale_, exponent_, inverseExponent_};
}

SkewInterpolator::SkewInterpolator(float minimum, float maximum, float midpoint)
    : Core::Interpolator(minimum, maximum, midpoint, nullptr),
      zoom_(0.f, 1.f, 1.f) {
  // Original app constructor initializes its embedded Zoom with these explicit
  // values and does not call the app setRange override here.
}
SkewInterpolator::SkewInterpolator(InterpolationPortTag,
                                   const InterpolationState &state)
    : Core::Interpolator(state[0], state[1], state[2]) {
  zoom_.seedPortable(state[3], state[4], state[5], state[6]);
}
SkewInterpolator::~SkewInterpolator() = default;
void SkewInterpolator::setRange(float minimum, float maximum, float midpoint) {
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  const float ratio =
      divide(subtract(midpoint, minimum), subtract(maximum, minimum));
  // Original binary32 literal 0xbf317218, not a recomputed double logarithm.
  const float power =
      divide(-0x1.62e43p-1f, presonus::dsp::detail::sourceLogf(ratio));
  zoom_.setRange(minimum, maximum, power);
}
float SkewInterpolator::normalizedToRange(float value) const {
  return zoom_.normalizedToRange(value);
}
float SkewInterpolator::rangeToNormalized(float value) const {
  return zoom_.rangeToNormalized(value);
}
InterpolationState SkewInterpolator::portableState() const {
  return {minRange,
          maxRange,
          midRange,
          zoom_.getMinRange(),
          zoom_.getMaxRange(),
          zoom_.getMidRange(),
          zoom_.portableReciprocal(),
          0};
}
} // namespace Presonus::Dsp
