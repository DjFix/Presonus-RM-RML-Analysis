#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

int main() {
  int input;
  while (std::cin >> input) {
    Presonus::Panel::ControlRegistrar receiver;
    receiver.bindPort(nullptr);
    int a, b, c, d;
    if (!(std::cin >> a >> b >> c >> d))
      return 2;
    Uart_Msg_Type message{
        {static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b),
         static_cast<std::uint8_t>(c), static_cast<std::uint8_t>(d)}};
    auto before = message.bytes;
    receiver.init();
    if (receiver.sourcePortVersion() != 0)
      return 3;
    receiver.handleVersion(input, message);
    std::cout << receiver.sourcePortVersion() << ' '
              << (before == message.bytes && receiver.getPort() == nullptr &&
                  receiver.sourcePortInitialized())
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
