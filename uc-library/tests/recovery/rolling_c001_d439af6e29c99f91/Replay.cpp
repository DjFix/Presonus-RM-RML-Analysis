#include "presonus/panel/Element.hpp"
#include <cstdlib>
#include <iostream>

using Presonus::Panel::Element;
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int seed = std::atoi(argv[1]);
  const bool value = seed % 2;
  Element element(seed, -seed);
  element.activate(seed + 1);
  element.setDirty(seed > 2 ? 0u : 81u);
  auto before = element.elementState();
  element.setNeedsToDraw(value);
  const auto &after = element.elementState();
  if (after.dirty != static_cast<unsigned>(value) ||
      element.needsToDraw() != value)
    return 1;
  std::cout << after.dirty << ' '
            << (after.x == before.x && after.y == before.y &&
                after.activation == before.activation)
            << " 0\n";
}
