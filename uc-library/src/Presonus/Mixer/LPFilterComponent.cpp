#include "presonus/mixer/LPFilterComponent.hpp"

namespace Presonus::Mixer {
LPFilterComponent::LPFilterComponent(SourcePortAudioLifecycle, const char *name,
                                     Dsp::Controller *controller,
                                     Core::IPropertyHandler *handler, int id)
    : Core::Portable::Component(name),
      audio_(std::in_place, name, controller, handler, id) {}

LPFilterComponent::~LPFilterComponent() = default;
} // namespace Presonus::Mixer
