#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

int main() {
  int input;
  while (std::cin >> input) {
    Presonus::Panel::ControlRegistrar receiver;
    receiver.bindPort(nullptr);
    auto *result = receiver.castTo(input);
    if (result && result != &receiver)
      return 2;
    std::cout << (result == &receiver) << ' '
              << (receiver.getPort() == nullptr &&
                  !receiver.sourcePortInitialized() &&
                  receiver.sourcePortVersion() == 0)
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
