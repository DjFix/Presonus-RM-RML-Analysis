#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
namespace Presonus::Mixer {
// Partial real type relationship from native RTTI; intermediate native bases
// intentionally omitted. Construction/state are source-port-only, not
// recovered.
class TalkbackInputComponent : public ChannelComponent {
public:
  DECLARE_CORE_CLASS(0x1742e4, TalkbackInputComponent, ChannelComponent)
  using ChannelComponent::ChannelComponent;
};
} // namespace Presonus::Mixer
