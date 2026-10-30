#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <cstdint>

namespace presonus::uart_message_port {
// Independent packet helper reproducing measured app-helper payload only.
// This does NOT declare/recover original setLedState or unknown kLedStates.
Uart_Msg_Type stateMessage(int group, int index, std::uint8_t state) {
  return {{0x4c, static_cast<std::uint8_t>(group),
           static_cast<std::uint8_t>(index), state}};
}
} // namespace presonus::uart_message_port
namespace Presonus {
void UARTMessageSender::setLedBrightness(unsigned char level) {
  // Original initializes only bytes0..1. Defined zero tail is a source-port
  // adaptation, never native uninitialized reads or original full-message ABI.
  Uart_Msg_Type message{{0x90, level, 0, 0}};
  port_.writeMsg(message);
}
void UARTMessageSender::setLedColorLinear(int index, int group, int color,
                                          bool turnOn) {
  const auto rgb = static_cast<std::uint32_t>(color);
  Uart_Msg_Type message{{0xa0, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(group),
                         static_cast<std::uint8_t>(rgb >> 16)}};
  port_.writeMsg(message);
  message.bytes[0] = 0xa1;
  message.bytes[3] = static_cast<std::uint8_t>(rgb >> 8);
  port_.writeMsg(message);
  message.bytes[0] = 0xa2;
  message.bytes[3] = static_cast<std::uint8_t>(rgb);
  port_.writeMsg(message);
  if (turnOn) {
    auto state = presonus::uart_message_port::stateMessage(group, index, 1);
    port_.writeMsg(state);
  }
}
void UARTMessageSender::setLedColor(int index, int group, RGBLedColors color,
                                    bool turnOn) {
  // Existing global source-port type is reused verbatim. Literal16 is observed
  // in original ARM; no new enumerator name/value or original underlying ABI.
  if (static_cast<int>(color) == 16) {
    auto state = presonus::uart_message_port::stateMessage(group, index, 3);
    port_.writeMsg(state);
    return;
  }
  Uart_Msg_Type message{{0x72, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(group),
                         static_cast<std::uint8_t>(static_cast<int>(color))}};
  port_.writeMsg(message);
  if (turnOn) {
    auto state = presonus::uart_message_port::stateMessage(group, index, 1);
    port_.writeMsg(state);
  }
}
} // namespace Presonus
