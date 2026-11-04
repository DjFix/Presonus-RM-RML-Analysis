#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <stdexcept>
namespace Presonus::Surface {
Presonus::IPanelPort *PanelRegistrar::getPort() const {
  if (!commandState_)
    throw std::logic_error("registrar port state must be explicitly bound");
  return commandState_->port;
}
} // namespace Presonus::Surface
