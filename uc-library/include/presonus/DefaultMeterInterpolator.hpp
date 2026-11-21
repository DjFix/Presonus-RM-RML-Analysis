#pragma once

#include "core/public/coreinterpolator.h"

// Portable lifecycle subset using the pinned SegmentInterpolator family.
// The original constructor, breakpoints and ARM fields remain unresolved.
class DefaultMeterInterpolator : public Core::SegmentInterpolator {
public:
  using SegmentInterpolator::SegmentInterpolator;
  ~DefaultMeterInterpolator() override;
};
