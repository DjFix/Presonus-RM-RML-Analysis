#include "presonus/mixer/GateComponent.hpp"

namespace Presonus::Mixer {
GateComponent::GateComponent(SourcePortAudioLifecycle, const char *name,
                             Dsp::Controller *controller,
                             Core::IPropertyHandler *handler, int id)
    : Core::Portable::Component(name),
      audio_(std::in_place, name, controller, handler, id) {}

GateComponent::~GateComponent() = default;
} // namespace Presonus::Mixer
