#pragma once
#include "core/public/gui/corecolor.h"
#include "core/public/gui/corerect.h"
#include <array>
#include <cstdint>

namespace Presonus {
// Source-port borrowed state. No original object layout or lifecycle is
// claimed.
class SpectrumPainter {
public:
  explicit SpectrumPainter(const Core::TRect<int> &last) : last_(last) {}
  Core::TRect<int> getLastDrawnRect() const;

private:
  const Core::TRect<int> &last_;
};
} // namespace Presonus
