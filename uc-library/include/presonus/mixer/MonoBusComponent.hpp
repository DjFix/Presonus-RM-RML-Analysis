#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
namespace Presonus::Mixer {
// Partial real type relationship from native RTTI; intermediate native bases
// intentionally omitted. Construction/state are source-port-only, not
// recovered.
class MonoBusComponent : public ChannelComponent {
public:
  DECLARE_CORE_CLASS(0x1765ec, MonoBusComponent, ChannelComponent)
  using ChannelComponent::ChannelComponent;
};
} // namespace Presonus::Mixer
