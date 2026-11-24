#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include <cstdint>
#include <iostream>

// Test carrier only. Production code has no definition or layout dependency.
namespace Presonus::Intercom {
class LinkEvent {
public:
  std::uint32_t sentinel;
};
} // namespace Presonus::Intercom

int main() {
  using namespace Presonus::Panel;
  Presonus::Mixer::MixerComponentBase mixer;
  presonus::panel_binding::PanelRegistrarPortState state;
  PanelRegistrar registrar(state);
  RackPanelComponent first(mixer, registrar), second(mixer, registrar);
  if (first.countParameters() != 5 || second.countParameters() != 5)
    return 1;
  for (auto *panel : {&first, &second, &first}) {
    for (auto sentinel : {0x10203040u}) {
      Presonus::Intercom::LinkEvent event{sentinel};
      panel->panelStatus = sentinel & 7;
      panel->permissionFlags = 5;
      const auto *parameter = panel->getParameterByTag(1);
      if (!parameter)
        return 2;
      panel->onCascadeStateChange();
      if (event.sentinel != sentinel || panel->panelStatus != (sentinel & 7) ||
          panel->permissionFlags != 5 || panel->mixer != &mixer ||
          panel->countParameters() != 5 ||
          panel->getParameterByTag(1) != parameter)
        return 3;
      std::cout << "unchanged\n";
    }
  }
}
