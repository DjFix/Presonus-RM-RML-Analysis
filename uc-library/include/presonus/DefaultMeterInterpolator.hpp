#pragma once

#include "core/public/coreinterpolator.h"

// Portable CCL-backed meter interpolator. Original ARM layout is unresolved.
class DefaultMeterInterpolator : public Core::SegmentInterpolator {
public:
  using SegmentInterpolator::SegmentInterpolator;
  DefaultMeterInterpolator();
  ~DefaultMeterInterpolator() override;
};

void __initMeterControl();
