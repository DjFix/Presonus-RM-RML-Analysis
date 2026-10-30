#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <cstdint>

namespace Presonus {
void UARTMessageSender::setPhantomPower(int, int index, bool enabled) {
  // Original initializes three bytes. Zero tail is a defined source-port
  // adaptation, not equivalence to the original uninitialized stack byte.
  Uart_Msg_Type message{{0x4d, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(enabled), 0}};
  port_.writeMsg(message);
}
void UARTMessageSender::setGainBoost(int, int index, bool enabled) {
  Uart_Msg_Type message{{0x41, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(enabled), 0}};
  // Real ProtocolComm's current codec rejects 'A' with -2. Preserve the real
  // provider behavior; never fabricate a successful gain-boost wire frame.
  port_.writeMsg(message);
}
} // namespace Presonus
