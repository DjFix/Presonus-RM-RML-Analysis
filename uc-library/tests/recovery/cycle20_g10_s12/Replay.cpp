#include "presonus/panel/StaticElement.hpp"

#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>

namespace {
using Presonus::Panel::StaticElement;
struct Derived final : StaticElement {
  Derived(int x, int y, const char *text) : StaticElement(x, y, text) {}
};

void report(const StaticElement &element) {
  const auto &state = element.elementState();
  std::cout << state.x << ' ' << state.y << ' ' << state.dirty;
  for (unsigned char byte : element.text())
    std::cout << ' ' << static_cast<int>(byte);
  std::cout << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  const int x = std::atoi(argv[2]), y = std::atoi(argv[3]);
  std::string source(argv[4]);
  if (std::string_view(argv[1]) == "C2") {
    const Derived element(x, y, source.c_str());
    source.clear();
    report(element);
  } else {
    const StaticElement element(x, y, source.c_str());
    source.clear();
    report(element);
  }
}
