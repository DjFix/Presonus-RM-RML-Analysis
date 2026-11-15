#pragma once
#include "presonus/mixer/MixerComponent.hpp"

namespace Presonus::Mixer {
// Partial portable source model. Native destruction delegates to
// MixerComponent; full original inheritance, member layout, constructor, EH and
// ARM ABI are unresolved. This tagged constructor is an independent source-port
// interface. MixerState and MixerServices are borrowed and must outlive this
// object.
class StormMixerComponent : public MixerComponent {
public:
  struct SourcePortConstruction {};
  StormMixerComponent(SourcePortConstruction,
                      presonus::mixer_component_port::MixerState &state,
                      presonus::mixer_component_port::MixerServices &services)
      : MixerComponent(state, services) {}
  ~StormMixerComponent() override;
};
} // namespace Presonus::Mixer
