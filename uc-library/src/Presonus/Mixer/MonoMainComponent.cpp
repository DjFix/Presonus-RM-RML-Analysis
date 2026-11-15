#include "presonus/mixer/MonoMainComponent.hpp"
namespace Presonus::Mixer {
// Compile this unit with -fno-sized-deallocation: native D0 calls _ZdlPv.
MonoMainComponent::~MonoMainComponent() = default;
} // namespace Presonus::Mixer
