#pragma once
#include "core/public/coreinterpolator.h"
namespace presonus::dsp {
// Independent test/source-port access friendship, not an original interface.
struct FaderInterpolatorSourceAccess;
} // namespace presonus::dsp
namespace Presonus::Dsp {
class FaderInterpolator : public Core::SegmentInterpolator {
public:
  FaderInterpolator();
  ~FaderInterpolator() override;
  // Actual CCL override contract; original unencoded return stays pending.
  void setRange(float minimum, float maximum, float midpoint = 1.f) override;
  // Original class data names/40bytes retained. Actual CCL element type and
  // const/array spelling are source-port choices, not original data ABI claims.
  static const Core::SegmentInterpolator::BreakPoint kCurvePoints84[5];
  static const Core::SegmentInterpolator::BreakPoint kCurvePoints96[5];

private:
  friend struct presonus::dsp::FaderInterpolatorSourceAccess;
};
} // namespace Presonus::Dsp
