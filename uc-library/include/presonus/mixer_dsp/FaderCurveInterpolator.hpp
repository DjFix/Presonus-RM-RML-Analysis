#pragma once
#include "core/public/coreinterpolator.h"

namespace Presonus::Dsp {
// Candidate source port using the actual pinned CCL base. The caller retains
// custom breakpoint storage for the complete interpolator lifetime. No original
// ARM layout, Core implementation behavior or hardware compatibility is
// claimed.
class FaderCurveInterpolator : public Core::SegmentInterpolator {
public:
  FaderCurveInterpolator();
  FaderCurveInterpolator(int count,
                         const Core::SegmentInterpolator::BreakPoint *points);
  ~FaderCurveInterpolator() override;
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  // Ordinary original return declarations are not encoded by these names.
  // Float is the explicit source-port contract pending independent evidence.
  float normalizedToDb(float value) const;
  float dbToNormalized(float value) const;

private:
  // Original data symbol and five pairs are established. Access/const spelling
  // is an explicit source-port choice, not recovered from object mangling.
  static const Core::SegmentInterpolator::BreakPoint kCurvePoints[5];
};
} // namespace Presonus::Dsp
