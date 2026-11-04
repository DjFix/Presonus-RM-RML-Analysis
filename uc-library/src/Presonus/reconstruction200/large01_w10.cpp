#include "presonus/reconstruction200/large01_w10.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <stdexcept>
namespace Presonus::Panel {
bool FrontPanelComponent::isValidToggleBook(int id) const {
  return static_cast<unsigned>(id) <= 11 && ((1U << id) & 0xce0U) != 0;
}
bool FrontPanelComponent::isCopyPasting() const {
  return state.copyContext != nullptr;
}
} // namespace Presonus::Panel
namespace Presonus::Surface {
Presonus::IPanelPort *PanelRegistrar::getPort() const {
  if (!commandState_)
    throw std::logic_error("registrar port state must be explicitly bound");
  return commandState_->port;
}
} // namespace Presonus::Surface

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
std::uint32_t FrontPanelComponent::getSendPidForAuxChannel(
    Presonus::Mixer::ChannelComponent &channel) {
  const presonus::frontpanel_port::ChannelRoute *route = nullptr;
  for (std::size_t i = 0; i < state.routeCount; ++i) {
    if (&state.routes[i].channel == &channel) {
      if (route)
        throw std::invalid_argument("duplicate channel route");
      route = &state.routes[i];
    }
  }
  if (!route)
    throw std::invalid_argument("channel route must be explicitly bound");
  std::uint32_t result = route->index + (route->category == 4 ? 224U : 300U);
  if (!route->linkable.isLinked())
    return result;
  if (route->index & 1U) {
    auto value = result - 224U;
    value += value >> 31;
    // Exact ARM arithmetic shift, without implementation-defined signed shift.
    value = (value >> 1) | (value & 0x80000000U);
    return value + 240U;
  }
  if (route->linkable.isLinkSlave())
    ++result;
  return result;
}
} // namespace Presonus::Panel
