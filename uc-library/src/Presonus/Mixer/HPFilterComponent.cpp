#include "presonus/mixer/HPFilterComponent.hpp"

#include "presonus/mixer/AudioComponent.hpp"
#include <utility>

namespace Presonus::Mixer {

HPFilterComponent::HPFilterComponent(SourcePortConstruction, const char *name)
    : Core::Portable::Component(name) {}

HPFilterComponent::HPFilterComponent(AdoptAudioComponent,
                                     std::unique_ptr<AudioComponent> audio,
                                     const char *name)
    : Core::Portable::Component(name), audio_(std::move(audio)) {}

HPFilterComponent::~HPFilterComponent() = default;

} // namespace Presonus::Mixer
