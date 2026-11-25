#include "presonus/mixer/LPFilterComponent.hpp"
#include "presonus/mixer_dsp/FilterControllers.hpp"

namespace Presonus::Mixer {
LPFilterComponent::LPFilterComponent(SourcePortAudioLifecycle, const char *name,
                                     Dsp::Controller *controller,
                                     Core::IPropertyHandler *handler, int id)
    : Core::Portable::Component(name),
      audio_(std::make_unique<AudioComponent>(name, controller, handler, id)) {}

LPFilterComponent::LPFilterComponent(const char *name,
                                     Core::IPropertyHandler *handler,
                                     int controllerId, int channelId)
    : Core::Portable::Component(name),
      audio_(presonus::dsp::makeLoPassAudioComponent(name, handler,
                                                     controllerId, channelId)) {
}

LPFilterComponent::~LPFilterComponent() = default;
} // namespace Presonus::Mixer
