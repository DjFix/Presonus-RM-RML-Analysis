#include "presonus/DefaultMeterInterpolator.hpp"

#include <array>

namespace {

// The firmware writes these fixed binary32 knots from its 13-entry dB table.
// Use the observed values so a host libm rounding difference cannot move a
// knot.
constexpr std::array<Core::SegmentInterpolator::BreakPoint, 13>
    meterCurvePoints{{
        {0x1.0efe72p-24f, 0x0.0p+0f},
        {0x1.26d42cp-11f, 0x1.555556p-4f},
        {0x1.9f7864p-10f, 0x1.555556p-3f},
        {0x1.04e748p-8f, 0x1p-2f},
        {0x1.04491p-7f, 0x1.555556p-2f},
        {0x1.03ab3ap-6f, 0x1.aaaaacp-2f},
        {0x1.030dc4p-5f, 0x1p-1f},
        {0x1.0270aap-4f, 0x1.2aaaacp-1f},
        {0x1.01d3f2p-3f, 0x1.555556p-1f},
        {0x1.013798p-2f, 0x1.8p-1f},
        {0x1.009b9cp-1f, 0x1.aaaaacp-1f},
        {0x1.96b23p-1f, 0x1.d55556p-1f},
        {0x1p+0f, 0x1p+0f},
    }};
constexpr char meterInterpolatorName[] = "audiometer";

} // namespace

DefaultMeterInterpolator::DefaultMeterInterpolator()
    : SegmentInterpolator(static_cast<int>(meterCurvePoints.size()),
                          meterCurvePoints.data()) {}

DefaultMeterInterpolator::~DefaultMeterInterpolator() = default;

void __initMeterControl() {
  Core::InterpolatorFactory::add(
      meterInterpolatorName,
      Core::InterpolatorFactory::createInterpolator<DefaultMeterInterpolator>);
}
