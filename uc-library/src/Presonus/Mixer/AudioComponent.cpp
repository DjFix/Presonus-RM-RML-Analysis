#include "presonus/mixer/AudioComponent.hpp"
#include "presonus/dsp/Controller.hpp"

namespace Presonus::Mixer {
AudioComponent::AudioComponent(const char *name, Dsp::Controller *controller,
                               Core::IPropertyHandler *handler, int id)
    : DspComponent(name, controller, dspcomponent_port::AdoptController{}),
      propertyHandler_(handler) {
  controller->sourceState().word04 = static_cast<std::uint32_t>(id);
  controller->setTarget(propertyHandler_);
}

AudioComponent::~AudioComponent() { propertyHandler_->release(); }
} // namespace Presonus::Mixer
