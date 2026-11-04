#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <stdexcept>
namespace Presonus::Panel {
const char *PanelRegistrar::getPanelPortName() { return "/dev/ttyS0"; }
Presonus::IPanelPort *PanelRegistrar::getPort() const { return state_.port; }
int PanelRegistrar::mapGroupIdToControlType(
    ControlRegistrar::ControlType id) const {
  switch (id) {
  case 0:
    return 12;
  case 1:
    return 13;
  case 2:
    return 15;
  default:
    return -1;
  }
}
} // namespace Presonus::Panel
