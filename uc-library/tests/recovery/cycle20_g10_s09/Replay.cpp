#include "presonus/panel/StaticElement.hpp"

#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  Presonus::Panel::StaticElement element(2, -7, "offline");
  element.activate(8);
  element.setDirty(static_cast<unsigned>(std::atoi(argv[1])));
  const auto before = element.elementState();
  element.setNeedsToDraw(std::atoi(argv[2]) != 0);
  const auto after = element.elementState();
  if (before.x != after.x || before.y != after.y ||
      before.activation != after.activation || element.text() != "offline")
    return 1;
  std::cout << after.dirty << '\n';
}
