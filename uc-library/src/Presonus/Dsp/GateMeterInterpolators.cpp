#include "presonus/mixer_dsp/GateMeterInterpolators.hpp"
namespace Presonus::Dsp {
const Core::SegmentInterpolator::BreakPoint
    GateRangeInterpolator::kCurvePoints[15] = {
        {0x0.0p+0f, -0x1.5000000000000p+6f},
        {0x1.1eb8520000000p-4f, -0x1.2000000000000p+6f},
        {0x1.1eb8520000000p-3f, -0x1.e800000000000p+5f},
        {0x1.ae147a0000000p-3f, -0x1.9800000000000p+5f},
        {0x1.28f5c20000000p-2f, -0x1.5000000000000p+5f},
        {0x1.70a3d80000000p-2f, -0x1.1000000000000p+5f},
        {0x1.b851ec0000000p-2f, -0x1.b000000000000p+4f},
        {0x1.0000000000000p-1f, -0x1.5000000000000p+4f},
        {0x1.23d70a0000000p-1f, -0x1.0000000000000p+4f},
        {0x1.47ae140000000p-1f, -0x1.8000000000000p+3f},
        {0x1.6b851e0000000p-1f, -0x1.2000000000000p+3f},
        {0x1.851eb80000000p-1f, -0x1.8000000000000p+2f},
        {0x1.c7ae140000000p-1f, -0x1.0000000000000p+2f},
        {0x1.dc28f60000000p-1f, -0x1.0000000000000p+1f},
        {0x1.0000000000000p+0f, 0x0.0p+0f}};
GateRangeInterpolator::GateRangeInterpolator()
    : Core::SegmentInterpolator(15, kCurvePoints) {}
GateRangeInterpolator::~GateRangeInterpolator() = default;
const Core::SegmentInterpolator::BreakPoint
    MeterCurveInterpolator::kMeterPoints[5] = {
        {0x0.0p+0f, -0x1.2000000000000p+7f},
        {0x1.47ae140000000p-5f, -0x1.e000000000000p+5f},
        {0x1.47ae140000000p-3f, -0x1.4000000000000p+5f},
        {0x1.0a3d700000000p-1f, -0x1.4000000000000p+3f},
        {0x1.0000000000000p+0f, 0x1.4000000000000p+3f}};
MeterCurveInterpolator::MeterCurveInterpolator()
    : FaderCurveInterpolator(5, kMeterPoints) {}
MeterCurveInterpolator::~MeterCurveInterpolator() = default;
} // namespace Presonus::Dsp
