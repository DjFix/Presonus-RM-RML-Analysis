#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace {
static_assert(sizeof(int) == 4 && std::numeric_limits<int>::digits == 31);
std::int32_t signedBits(std::uint32_t bits) {
  return static_cast<std::int32_t>(static_cast<std::int64_t>(bits) -
                                   ((bits & 0x80000000U) ? 0x100000000LL : 0));
}
int bumpParameter(Core::Portable::Parameter &parameter,
                  presonus::surface::PanelRegistrarCommandState *state,
                  int delta, std::uint8_t opcode) {
  const float value = parameter.getValue();
  if (!std::isfinite(value) || value < -0x1p31f || value >= 0x1p31f)
    throw std::domain_error("finite signed32 fader getter required");
  const auto previous = static_cast<std::int32_t>(value);
  const auto sum = signedBits(static_cast<std::uint32_t>(previous) +
                              static_cast<std::uint32_t>(delta));
  std::int32_t next;
  if (delta > 0)
    next = sum >= 7 ? 7 : sum;
  else {
    const auto negated = signedBits(0U - static_cast<std::uint32_t>(delta));
    next = previous < negated ? 0 : sum;
  }
  if (next != previous) {
    parameter.setValue(static_cast<float>(next), false);
    // The setter may synchronously reselect the borrowed live port.
    if (!state || !state->port)
      throw std::logic_error("live borrowed panel port required after setter");
    Presonus::IPanelPort *port = state->port;
    // Only prefix2 initialized in the original; zero tail is a source
    // adaptation.
    Uart_Msg_Type message{{opcode, static_cast<unsigned char>(next), 0, 0}};
    port->writeMsg(message);
  }
  return next;
}
} // namespace
namespace Presonus::Surface {
int PanelRegistrar::bumpFaderTouchSensitivity(int delta) {
  if (!parameters_)
    throw std::logic_error("borrowed parameter list required");
  return bumpParameter(*parameters_->byTag(901), commandState_, delta, 'H');
}
int PanelRegistrar::bumpFaderSpeed(int delta) {
  if (!parameters_)
    throw std::logic_error("borrowed parameter list required");
  return bumpParameter(*parameters_->byTag(900), commandState_, delta, 'v');
}
} // namespace Presonus::Surface
