#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/MackieControlModel.hpp"
// Intentional partial source-port classes. The application destructor ranges
// only reset dispatch pointers and call Component destruction. Using the real
// pinned provider as a base models that cleanup; original inheritance, complete
// fields, vtable addresses and ARM32 layout are not established.
namespace Presonus::Surface {
class StartPageComponent : public Core::Portable::Component {
public:
  ~StartPageComponent();
  // Provisional bool declarations; caller must provide actual NumericParam
  // tags 1000/1001 in the inherited CCL collection. Original layout/ABI
  // pending.
  bool isDawMode() const;
  bool isMidiMode() const;
};
} // namespace Presonus::Surface
