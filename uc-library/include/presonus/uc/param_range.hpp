#pragma once

#include "core/public/corestringbuffer.h"

namespace Presonus::UC {

// Portable values identified through ParamRangeElement and ParamElement.
// Field declarations and representation are independent of the ARM layout.
struct ParamRange {
  ParamRange();

  double minimum = 0.0;
  double maximum = 1.0;
  double midpoint = 0.0;
  double defaultValue = 0.0;
  int steps = 0;
  Core::CString64 units;
  Core::CString64 curve;
};
} // namespace Presonus::UC
