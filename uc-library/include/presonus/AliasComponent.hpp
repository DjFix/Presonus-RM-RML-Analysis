#pragma once

#include "core/portable/corecomponent.h"

namespace Presonus {

// Bounded portable source port. The original constructor calls Component and
// clears the pointer consumed by setOriginal(Component*) at ARM offset 0x84.
// This uses the actual CCL provider layout, not the original ARM object layout.
class AliasComponent : public Core::Portable::Component {
public:
  explicit AliasComponent(const char *name);

private:
  // The original D1/D2 bodies perform no app-specific referent cleanup.
  Core::Portable::Component *original;
  friend struct AliasComponentSourcePortProbe;
};

} // namespace Presonus
