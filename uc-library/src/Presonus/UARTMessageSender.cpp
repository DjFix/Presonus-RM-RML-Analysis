#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <cstdint>

namespace Presonus {
void UARTMessageSender::setFaderPosition(int index, int position) {
  const auto value = static_cast<std::uint16_t>(position);
  Uart_Msg_Type message{{0x66, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(value),
                         static_cast<std::uint8_t>(value >> 8)}};
  port_.writeMsg(message);
}
void UARTMessageSender::setDigitalPot(int, int index, int value) {
  // Original writes exactly bytes0..2; byte3 is uninitialized stack storage.
  // Defined source-port adaptation: zero that unused codec byte. No native
  // uninitialized read, original full-message/wire or virtual ABI claim.
  Uart_Msg_Type message{{0x64, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(value), 0}};
  port_.writeMsg(message);
}
} // namespace Presonus
