#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
namespace Presonus::Mixer {
// Bounded portable source port. Native instructions delegate to
// ChannelComponent; original full construction, fields, intermediate bases and
// ARM ABI are unknown.
class MonoMainComponent : public ChannelComponent {
public:
  struct SourcePortConstruction {};
  MonoMainComponent(SourcePortConstruction,
                    presonus::mixer::ChannelState &state)
      : ChannelComponent(ChannelComponent::SourcePortConstruction{}, state) {}
  ~MonoMainComponent() override;
};
} // namespace Presonus::Mixer
