#include "presonus/mixer/setup_property_applications.hpp"

#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/uart_message.hpp"
#include <stdexcept>

namespace Presonus::Mixer {
void RackMixerApplication::onProgress(const char *, float progress) {
  if (!progressRegistrar_)
    throw std::logic_error("Rack mixer progress registrar is not bound");
  if (!(progress >= 0.0f && progress <= 1.0f))
    throw std::out_of_range("Rack mixer progress must be in [0, 1]");

  const auto ticks = static_cast<std::uint16_t>(progress * 16.0f);
  Uart_Msg_Type message{{0x67, 0x0c, static_cast<std::uint8_t>(ticks),
                         static_cast<std::uint8_t>(ticks >> 8)}};
  if (auto *port = progressRegistrar_->getPort())
    port->writeMsg(message);
}
} // namespace Presonus::Mixer
