#include "presonus/mixer/StormMixerComponent.hpp"

namespace Presonus::Mixer {
// Native D2 resets dispatch then calls MixerComponent destruction. There is no
// additional derived cleanup in the bounded source port. Compile this unit with
// -fno-sized-deallocation: native D0 calls unsized global operator delete.
StormMixerComponent::~StormMixerComponent() = default;
} // namespace Presonus::Mixer
