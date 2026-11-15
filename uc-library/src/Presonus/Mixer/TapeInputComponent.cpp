#include "presonus/mixer/TapeInputComponent.hpp"
namespace Presonus::Mixer {
// Original D1 calls ChannelComponent D2; original D0 then calls unsized delete.
// Compile this unit with -fno-sized-deallocation to preserve that boundary.
TapeInputComponent::~TapeInputComponent() = default;
} // namespace Presonus::Mixer
