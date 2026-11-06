#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus::Mixer {
// Partial portable source port. Component inheritance is an intentional CCL
// integration, not a recovered original layout or constructor declaration.
class FilterGroupComponent : public Core::Portable::Component {
public:
  // Independent CCL class query; not original RTTI/ABI proof.
  DECLARE_CORE_CLASS(0x31c45c, FilterGroupComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit FilterGroupComponent(SourcePortConstruction)
      : Core::Portable::Component("filterGroup") {}

  // Provisional bool: the ordinary ELF name does not encode the return type.
  bool isConfigured();
};
} // namespace Presonus::Mixer
