#include "presonus/mixer/EQComponent.hpp"

namespace Presonus::Mixer {
EQComponent::EQComponent(SourcePortAudioLifecycle, const char *name,
                         Dsp::Controller *controller,
                         Core::IPropertyHandler *handler, int id)
    : Core::Portable::Component(name),
      audio_(std::in_place, name, controller, handler, id) {}

EQComponent::~EQComponent() = default;
} // namespace Presonus::Mixer
