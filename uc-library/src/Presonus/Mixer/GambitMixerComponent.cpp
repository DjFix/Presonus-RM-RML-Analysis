#include "presonus/mixer/GambitMixerComponent.hpp"
namespace Presonus::Mixer {
std::int32_t GambitMixerComponent::numHWMicLineIn() const { return 16; }
std::int32_t GambitMixerComponent::getDanteTalkbackSlot() { return 57; }
} // namespace Presonus::Mixer
