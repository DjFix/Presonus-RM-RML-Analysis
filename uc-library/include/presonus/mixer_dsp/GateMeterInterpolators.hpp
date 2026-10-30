#pragma once
#include "presonus/mixer_dsp/FaderCurveInterpolator.hpp"
namespace Presonus::Dsp {
// Portable CCL-backed source declarations; original ARM layout is not claimed.
class GateRangeInterpolator : public Core::SegmentInterpolator {
public:
  GateRangeInterpolator();
  ~GateRangeInterpolator() override;

private:
  // Original data identities/bytes established; access and const are port
  // choices.
  static const Core::SegmentInterpolator::BreakPoint kCurvePoints[15];
};
class MeterCurveInterpolator : public FaderCurveInterpolator {
public:
  MeterCurveInterpolator();
  ~MeterCurveInterpolator() override;

private:
  static const Core::SegmentInterpolator::BreakPoint kMeterPoints[5];
};
} // namespace Presonus::Dsp
