#include "presonus/panel/BeastFrontPanelComponent.hpp"
#include <iostream>
int main() {
  Presonus::Mixer::MixerComponentBase m;
  Presonus::Panel::BeastFrontPanelComponent x(m);
  int groups[] = {0, 1, 2, -1, 3, 2147483647, (-2147483647 - 1)};
  int a = 1, b = 2;
  for (int g : groups) {
    const int *first = &a;
    const int *second = &b;
    int count = 77;
    x.getTablesForGroup(g, first, second, count);
    std::cout << count << ' ';
    if (g >= 0 && g < 3) {
      for (int i = 0; i < 34; ++i)
        std::cout << first[i] << ' ';
      for (int i = 0; i < 20; ++i)
        std::cout << second[i] << ' ';
    } else
      std::cout << (first == &a) << ' ' << (second == &b);
    std::cout << '\n';
  }
}
