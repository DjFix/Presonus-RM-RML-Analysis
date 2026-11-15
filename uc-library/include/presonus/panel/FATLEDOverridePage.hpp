#pragma once
#include "core/portable/coreparams.h"
namespace Presonus::Panel {
// Partial source-port composition. Borrow the actual NumericParam observed at
// native +0x11c; null is supported. No original layout/inheritance claim.
class FATLEDOverridePage {
public:
  struct SourcePortConstruction {};
  FATLEDOverridePage(SourcePortConstruction,
                     Core::Portable::NumericParam *overrideParameter)
      : overrideParameter_(overrideParameter) {}
  // Ordinary return declaration unresolved; provisional portable void.
  void deactivate();

private:
  Core::Portable::NumericParam *overrideParameter_;
};
} // namespace Presonus::Panel
