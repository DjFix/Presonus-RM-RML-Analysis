#pragma once
#include "core/public/gui/corecolor.h"
namespace Presonus {
// RTTI/vtable evidence establishes this original interface and virtual cleanup.
// Return spellings are portable source choices, not recovered declarations.
class IColorConverter {
public:
  virtual ~IColorConverter();
  virtual int getColorIndexForRGB(const Core::Color &) const = 0;
  virtual Core::Color getRGBFromColorIndex(int) const = 0;
};
} // namespace Presonus
