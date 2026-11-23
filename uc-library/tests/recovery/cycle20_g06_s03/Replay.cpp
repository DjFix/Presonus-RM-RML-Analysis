#include "presonus/panel/Element.hpp"

#include <iostream>
#include <string_view>

using Presonus::Panel::Element;

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string_view mode(argv[1]);
  if (mode == "element-constructor") {
    int x, y;
    while (std::cin >> x >> y) {
      Element element(x, y);
      const auto &state = element.elementState();
      std::cout << state.x << ' ' << state.y << ' ' << state.dirty << ' '
                << state.activation << '\n';
    }
  } else if (mode == "activation") {
    int prior, next;
    unsigned int dirty;
    while (std::cin >> prior >> next >> dirty) {
      Element element;
      Element &receiver = element;
      receiver.activate(prior);
      element.setDirty(dirty);
      receiver.activate(next);
      const auto &state = receiver.elementState();
      std::cout << state.dirty << ' ' << state.activation << '\n';
    }
  } else {
    return 2;
  }
}
