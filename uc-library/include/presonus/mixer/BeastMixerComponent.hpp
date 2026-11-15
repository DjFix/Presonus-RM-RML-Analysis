#pragma once
#include "presonus/mixer/MixerComponent.hpp"

namespace Presonus::Mixer {
// Bounded portable lifecycle interface. The native destructor delegates to
// MixerComponent; its full original constructor, members, multiple inheritance,
// vtable layout, exceptions and ARM32 ABI remain unresolved. Native vptr stores
// are compiler lifecycle operations, not portable application fields.
class BeastMixerComponent : public MixerComponent {
public:
  // Independent construction only; this is not a recovered original
  // constructor.
  struct SourcePortConstruction {};
  BeastMixerComponent(SourcePortConstruction,
                      presonus::mixer_component_port::MixerState &state,
                      presonus::mixer_component_port::MixerServices &services)
      : MixerComponent(state, services) {}
  // Real canonical base destruction preserves its borrowed state and services.
  // Compile this implementation with -fno-sized-deallocation to retain the
  // observed unsized global delete boundary in the generated D0 variant.
  ~BeastMixerComponent() override;
};
} // namespace Presonus::Mixer
