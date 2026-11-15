#include "presonus/panel/BeastPanelRegistrar.hpp"
#include <iostream>
int main() {
  Presonus::Panel::BeastPanelRegistrar x;
  int groups[] = {
      0,  1,  2,          3,    4,  5,  6,  7,  8,  9,
      10, 11, 12,         13,   14, 15, 16, -1, -2, (-2147483647 - 1),
      17, 18, 2147483647, 65536};
  for (int g : groups)
    std::cout << x.getParamInfoListSizeFromGroup(g) << ' ';
  std::cout << '\n';
}
