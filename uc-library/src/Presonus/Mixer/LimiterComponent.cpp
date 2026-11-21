#include "presonus/mixer/LimiterComponent.hpp"

#include "presonus/mixer/AudioComponent.hpp"
#include <utility>

namespace Presonus::Mixer {

LimiterComponent::LimiterComponent(SourcePortConstruction, const char *name)
    : Core::Portable::Component(name) {}

LimiterComponent::LimiterComponent(AdoptAudioComponent,
                                   std::unique_ptr<AudioComponent> audio,
                                   const char *name)
    : Core::Portable::Component(name), audio_(std::move(audio)) {}

LimiterComponent::~LimiterComponent() = default;

} // namespace Presonus::Mixer
