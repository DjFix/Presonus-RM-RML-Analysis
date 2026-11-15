#include "presonus/panel/RoguePanelRegistrar.hpp"
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int group = std::atoi(argv[1]);
  Presonus::Panel::RoguePanelRegistrar object;
  int count = 0x13579bdf;
  auto *p = object.getTags(group, count);
  std::cout << (p ? 1 : 0) << " " << count;
  if (p) {
    auto *q = object.getTags(group, count);
    if (p != q)
      return 3;
    for (int i = 0; i < count; ++i)
      std::cout << " " << p[i];
  }
  std::cout << "\n";
}
