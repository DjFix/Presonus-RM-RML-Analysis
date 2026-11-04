#pragma once

#include "core/portable/gui/corecontrols.h"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class McuVpotControl : public Core::Portable::Slider {
public:
  McuVpotControl(const Core::TRect<int> &size,
                 Core::Portable::Parameter *parameter);
  struct PortableState {
    Core::Portable::Bitmap *image;
    Core::Portable::Bitmap *strip;
    Core::Portable::Bitmap *slice;
    int value;
  };
  PortableState portableState() const;

protected:
  Core::Portable::BitmapReference image_, strip_, slice_;
  int value_;
};
} // namespace Presonus
