#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

int main() {
  int input;
  while (std::cin >> input) {
    Presonus::Panel::ControlRegistrar receiver;
    receiver.bindPort(nullptr);
    if (receiver.sourcePortInitialized())
      return 2;
    Uart_Msg_Type version{{0, 0, 0x34, 0x12}};
    receiver.handleVersion(0, version);
    if (input == 1)
      receiver.init();
    receiver.init();
    std::cout << receiver.sourcePortInitialized() << ' '
              << (receiver.sourcePortVersion() == 0x1234 &&
                  receiver.getPort() == nullptr)
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
