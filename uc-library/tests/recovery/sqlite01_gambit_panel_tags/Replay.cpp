#include "presonus/panel/GambitPanelRegistrar.hpp"

#include <iostream>

int main() {
  const Presonus::Panel::GambitPanelRegistrar first, second;
  int group = 0;
  int initialCount = 0;
  unsigned receiver = 0;
  while (std::cin >> group >> initialCount >> receiver) {
    if (receiver != 0 && receiver != 1)
      return 1;
    struct {
      unsigned left;
      int count;
      unsigned right;
    } guarded{0xCADFBEDA, initialCount, 0xDABEDFAC};
    const auto &registrar = receiver == 0 ? first : second;
    const auto *tags = registrar.getTags(group, guarded.count);
    std::cout << (tags != nullptr) << ' ' << guarded.count << ' '
              << guarded.left << ' ' << guarded.right << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
