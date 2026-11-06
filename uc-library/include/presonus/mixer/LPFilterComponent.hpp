#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Mixer {
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases; no original
// lifecycle/layout claim.
class LPFilterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x173358, LPFilterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit LPFilterComponent(SourcePortConstruction, const char *name = "")
      : Core::Portable::Component(name) {}
};
} // namespace Presonus::Mixer
