#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Mixer {
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases; no original
// lifecycle/layout claim.
class HPFilterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x1733f0, HPFilterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit HPFilterComponent(SourcePortConstruction, const char *name = "")
      : Core::Portable::Component(name) {}
};
} // namespace Presonus::Mixer
