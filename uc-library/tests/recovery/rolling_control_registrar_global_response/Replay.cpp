#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

int main() {
  int type;
  unsigned first, selector, low, high;
  while (std::cin >> type >> first >> selector >> low >> high) {
    Presonus::Panel::ControlRegistrar registrar;
    registrar.bindPort(nullptr);
    registrar.init();
    Uart_Msg_Type prior{{0, 0, 0xde, 0xac}};
    registrar.handleVersion(0, prior);
    Uart_Msg_Type message{
        {static_cast<std::uint8_t>(first), static_cast<std::uint8_t>(selector),
         static_cast<std::uint8_t>(low), static_cast<std::uint8_t>(high)}};
    const auto original = message.bytes;
    registrar.handleGlobalResponse(type, message);
    if (message.bytes != original || !registrar.sourcePortInitialized() ||
        registrar.getPort() != nullptr)
      return 1;
    std::cout << registrar.sourcePortVersion() << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
