#pragma once
#include "core/public/coreinterpolator.h"
#include <array>

namespace presonus::dsp {
// Independent semantic-state fixture API; not original field spellings/layout.
using InterpolationState = std::array<float, 8>;
struct InterpolationPortTag {};
namespace detail {
// Actual pinned Core type, with an independent state observation/seeding API.
class SourceZoomState : public Core::ZoomInterpolator {
public:
  SourceZoomState();
  SourceZoomState(float low, float high, float power);
  ~SourceZoomState() override;
  void seedPortable(float low, float high, float power, float reciprocal);
  float portableReciprocal() const;
};
} // namespace detail
} // namespace presonus::dsp

namespace Presonus::Dsp {
// These source-port classes use the real CCL base and implementations.
// Runtime RTTI/dynamic_cast is unsupported with the chosen no-RTTI provider.
// Tagged constructors are independent adapters. Original required-argument
// lifecycle interfaces are source ports; no original ARM layout is claimed.
class RatioInterpolator : public Core::Interpolator {
public:
  RatioInterpolator(float minimum, float maximum);
  RatioInterpolator(presonus::dsp::InterpolationPortTag,
                    const presonus::dsp::InterpolationState &);
  ~RatioInterpolator() override;
  void setRange(float minimum, float maximum, float midpoint) override;
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  presonus::dsp::InterpolationState portableState() const;

private:
  Core::LinearInterpolator linear_;
};

class ExpInterpolator : public Core::Interpolator {
public:
  // Required original parameters; no default arguments recovered.
  // Invalid initial ranges can leave inverse state indeterminate, as original.
  ExpInterpolator(float minimum, float maximum, float midpoint);
  ExpInterpolator(presonus::dsp::InterpolationPortTag,
                  const presonus::dsp::InterpolationState &);
  ~ExpInterpolator() override;
  void setRange(float minimum, float maximum, float midpoint) override;
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  presonus::dsp::InterpolationState portableState() const;

private:
  float offset_, scale_, inverseScale_, exponent_, inverseExponent_;
};

class SkewInterpolator : public Core::Interpolator {
public:
  SkewInterpolator(float minimum, float maximum, float midpoint);
  SkewInterpolator(presonus::dsp::InterpolationPortTag,
                   const presonus::dsp::InterpolationState &);
  ~SkewInterpolator() override;
  void setRange(float minimum, float maximum, float midpoint) override;
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  presonus::dsp::InterpolationState portableState() const;

private:
  presonus::dsp::detail::SourceZoomState zoom_;
};
} // namespace Presonus::Dsp
