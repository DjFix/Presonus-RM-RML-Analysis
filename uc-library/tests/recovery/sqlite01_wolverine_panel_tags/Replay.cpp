#include "presonus/panel/WolverinePanelRegistrar.hpp"
#include <iostream>

int main() {
  const Presonus::Panel::WolverinePanelRegistrar first;
  const Presonus::Panel::WolverinePanelRegistrar second;
  int group;
  int count;
  unsigned receiver;
  while (std::cin >> group >> count >> receiver) {
    const auto &registrar = receiver == 0 ? first : second;
    const int *tags = registrar.getTags(group, count);
    std::cout << (tags == nullptr) << ' ' << count << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
