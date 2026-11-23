#include "presonus/panel/FillElement.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
using Presonus::Panel::FillElement;
struct Derived final : FillElement {
  Derived(int x, int y, int w, int h, int v) : FillElement(x, y, w, h, v) {}
};

void report(const FillElement &element) {
  const auto &state = element.elementState();
  const auto &rect = element.fillRectangle();
  std::cout << state.x << ' ' << state.y << ' ' << rect.width << ' '
            << rect.height << ' ' << rect.x << ' ' << rect.y << ' '
            << rect.width << ' ' << rect.height << ' '
            << element.sourcePortFillValue() << ' ' << state.dirty << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  const int x = std::atoi(argv[2]), y = std::atoi(argv[3]);
  const int w = std::atoi(argv[4]), h = std::atoi(argv[5]),
            value = std::atoi(argv[6]);
  if (std::string_view(argv[1]) == "C2") {
    const Derived element(x, y, w, h, value);
    report(element);
  } else {
    const FillElement element(x, y, w, h, value);
    report(element);
  }
}
