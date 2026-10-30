#include "presonus/mixer_dsp/FaderCurveInterpolator.hpp"
#include "Power.hpp"
#include <cmath>

namespace {
constexpr float minimumAmplitude = 0x1.0efe7ep-24f;
} // namespace

namespace Presonus::Dsp {
const Core::SegmentInterpolator::BreakPoint
    FaderCurveInterpolator::kCurvePoints[] = {{0.f, -144.f},
                                              {0.04f, -60.f},
                                              {0.16f, -40.f},
                                              {0.52f, -10.f},
                                              {1.f, 10.f}};
FaderCurveInterpolator::FaderCurveInterpolator()
    : Core::SegmentInterpolator(5, kCurvePoints) {}
FaderCurveInterpolator::FaderCurveInterpolator(
    int count, const Core::SegmentInterpolator::BreakPoint *points)
    : Core::SegmentInterpolator(count, points) {}
FaderCurveInterpolator::~FaderCurveInterpolator() = default;

float FaderCurveInterpolator::normalizedToDb(float value) const {
  return Core::SegmentInterpolator::normalizedToRange(value);
}
float FaderCurveInterpolator::dbToNormalized(float value) const {
  return Core::SegmentInterpolator::rangeToNormalized(value);
}
float FaderCurveInterpolator::normalizedToRange(float value) const {
  const float db = Core::SegmentInterpolator::normalizedToRange(value);
  if (db < -144.f)
    return minimumAmplitude;
  return presonus::dsp::detail::sourcePowf(10.f, db * 0x1.99999ap-5f);
}
float FaderCurveInterpolator::rangeToNormalized(float value) const {
  const float db = value < minimumAmplitude ? -144.f : ::log10f(value) * 20.f;
  return Core::SegmentInterpolator::rangeToNormalized(db);
}
} // namespace Presonus::Dsp
