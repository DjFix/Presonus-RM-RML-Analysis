#include "core/portable/coreattributes.h"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelComponent.hpp"

namespace presonus::panel_port {
PanelCore::~PanelCore() = default;
}

namespace Presonus::Panel {
PanelComponent::PanelComponent(Presonus::Mixer::MixerComponentBase &mixer,
                               PanelRegistrar &registrar)
    : services(checkedServices) {
  portable.mixer = &mixer;
  portable.registrar = &registrar;
}
PanelComponent::~PanelComponent() = default;
} // namespace Presonus::Panel
