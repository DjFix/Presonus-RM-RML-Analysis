#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include <iostream>
// Opaque host test carrier. The reconstructed method does not inspect it.
namespace Presonus::Intercom {
class LinkEvent {
public:
  unsigned sentinel;
};
} // namespace Presonus::Intercom
int main() {
  Presonus::Mixer::MixerComponentBase mixer;
  presonus::panel_binding::PanelRegistrarPortState registrarState;
  Presonus::Panel::PanelRegistrar registrar(registrarState);
  for (unsigned pattern : {0u, 5u, 9u}) {
    Presonus::Panel::FrontPanelComponent panel(mixer, registrar);
    auto &state = panel.portableFrontState();
    state.panelMode = pattern;
    Presonus::Intercom::LinkEvent event{pattern};
    const int parameters = panel.portableState().component.countParameters();
    panel.processLinkEvent(event);
    if (event.sentinel != pattern ||
        state.panelMode != static_cast<int>(pattern) ||
        panel.portableState().component.countParameters() != parameters)
      return 1;
    std::cout << "unchanged\n";
  }
}
