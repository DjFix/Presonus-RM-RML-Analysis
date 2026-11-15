#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
namespace Presonus::Mixer {
// Bounded source port: actual canonical ChannelComponent/CCL lifecycle.
// Original complete hierarchy, constructor, members and ARM layout are unknown.
// No new owning derived members are established by the observed destructor.
class TapeInputComponent : public ChannelComponent {
public:
  struct SourcePortConstruction {};
  TapeInputComponent(SourcePortConstruction,
                     presonus::mixer::ChannelState &state,
                     presonus::mixer::ChannelApplicationServices &services)
      : ChannelComponent(state, services) {}
  ~TapeInputComponent() override;
};
} // namespace Presonus::Mixer
