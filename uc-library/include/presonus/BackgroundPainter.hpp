#pragma once
#include "core/portable/gui/coreviewshared.h"
namespace Presonus {
// Portable original-scope interface. Original ordinary return, inheritance and
// object/ARM ABI layout are unresolved. Painters are borrowed by EQControl.
class BackgroundPainter {
public:
  virtual void paint(const Core::TRect<int> &rectangle,
                     const Core::Portable::DrawEvent &event,
                     const Core::Portable::Style &style);
  virtual ~BackgroundPainter() = default;
};
} // namespace Presonus
