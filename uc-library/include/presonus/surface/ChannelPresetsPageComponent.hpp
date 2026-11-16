#pragma once
#include "presonus/surface/PresetsPageComponent.hpp"
namespace Presonus::Surface {
// Partial source-port inheritance expresses the observed common cleanup only.
// It does not establish original inheritance, constructors, layout or ARM ABI.
class ChannelPresetsPageComponent : public PresetsPageComponent {
public:
  using PresetsPageComponent::PresetsPageComponent;
  ~ChannelPresetsPageComponent() override;
};
} // namespace Presonus::Surface
