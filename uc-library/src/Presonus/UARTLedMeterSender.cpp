#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <cstdint>

namespace Presonus {
void UARTMessageSender::setLedMeterPosition(int, int index, int value) {
  Uart_Msg_Type message{{0x56, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(value), 0}};
  port_.writeMsg(message);
}
void UARTMessageSender::setLedMeterPositionCA(int, int index, int value) {
  Uart_Msg_Type message{{0x56, static_cast<std::uint8_t>(index),
                         static_cast<std::uint8_t>(value), 2}};
  port_.writeMsg(message);
}
void UARTMessageSender::setLedMeterClip(int, int index) {
  Uart_Msg_Type message{{0x4e, static_cast<std::uint8_t>(index), 7, 1}};
  port_.writeMsg(message);
}
} // namespace Presonus
