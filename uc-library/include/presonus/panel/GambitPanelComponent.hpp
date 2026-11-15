#pragma once
#include "presonus/panel/RackPanelComponent.hpp"

namespace Presonus::Panel {
// Bounded portable source port of the observed destructor delegation. The
// original complete constructor, members, multiple-base layout and ARM ABI are
// unresolved. This tag explicitly identifies independent host construction.
class GambitPanelComponent : public RackPanelComponent {
public:
  struct SourcePortConstruction {};
  GambitPanelComponent(SourcePortConstruction,
                       presonus::rackpanel_port::Dependencies &dependencies)
      : RackPanelComponent(dependencies) {}
  ~GambitPanelComponent() override;
};
} // namespace Presonus::Panel
