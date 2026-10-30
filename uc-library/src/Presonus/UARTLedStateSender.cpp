#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <cstdint>

namespace presonus::uart_message_port {
// Reuse the independent, already validated packet builder in the frozen
// color candidate. It is not an original helper/type declaration.
Uart_Msg_Type stateMessage(int, int, std::uint8_t);
} // namespace presonus::uart_message_port
namespace Presonus {
void UARTMessageSender::setLedState(int group, int index, kLedStates state) {
  // Type identity is provisional beyond the encoded global name; only raw-word
  // low8 behavior is compared. No original enum kind/underlying/ABI claim.
  auto message = presonus::uart_message_port::stateMessage(
      group, index, static_cast<std::uint8_t>(state));
  port_.writeMsg(message);
}
} // namespace Presonus
