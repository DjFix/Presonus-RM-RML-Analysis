#pragma once
#include "presonus/panel/FrontPanelComponent.hpp"
namespace Presonus::Panel {
// Partial portable class: native destructor delegates to the real FrontPanel
// provider. Original multiple inheritance, vptr offsets and ARM ABI unresolved.
class Fat24FrontPanelComponent : public FrontPanelComponent {
public:
  struct SourcePortConstruction {};
  explicit Fat24FrontPanelComponent(SourcePortConstruction)
      : FrontPanelComponent(FrontPanelComponent::SourcePortConstruction{}) {}
  ~Fat24FrontPanelComponent() override;
};
} // namespace Presonus::Panel
