#include "presonus/mixer_dsp/FaderInterpolator.hpp"
namespace Presonus::Dsp {
const Core::SegmentInterpolator::BreakPoint
    FaderInterpolator::kCurvePoints84[5] = {
        {0x0.0p+0f, -0x1.5000000000000p+6f},
        {0x1.0624de0000000p-8f, -0x1.e000000000000p+5f},
        {0x1.70a3d80000000p-4f, -0x1.4000000000000p+5f},
        {0x1.e147ae0000000p-2f, -0x1.4000000000000p+3f},
        {0x1.0000000000000p+0f, 0x1.4000000000000p+3f},
};
const Core::SegmentInterpolator::BreakPoint
    FaderInterpolator::kCurvePoints96[5] = {
        {0x0.0p+0f, -0x1.8000000000000p+6f},
        {0x1.0624de0000000p-8f, -0x1.e000000000000p+5f},
        {0x1.70a3d80000000p-4f, -0x1.4000000000000p+5f},
        {0x1.e147ae0000000p-2f, -0x1.4000000000000p+3f},
        {0x1.0000000000000p+0f, 0x1.4000000000000p+3f},
};
FaderInterpolator::FaderInterpolator()
    : Core::SegmentInterpolator(5, kCurvePoints84) {}
FaderInterpolator::~FaderInterpolator() = default;
void FaderInterpolator::setRange(float minimum, float maximum, float midpoint) {
  // Pinned Core::SegmentInterpolator::setRange is deliberately a no-op.
  // This app override writes the actual inherited Interpolator range fields.
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  if (minimum == -96.f && maximum == 10.f)
    breakPoints = kCurvePoints96;
  else if (minimum == -84.f && maximum == 10.f)
    breakPoints = kCurvePoints84;
  // All other inputs preserve the current borrowed curve pointer.
}
} // namespace Presonus::Dsp
