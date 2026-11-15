#include "presonus/panel/RogueFrontPanelComponent.hpp"
#include <iostream>
#include <stdexcept>
static void print(const int *p) {
  for (int i = 0; i < 26; ++i) {
    std::cout << ' ' << p[i];
    if (p[i] == -1)
      return;
  }
  throw std::runtime_error("table sentinel absent");
}
int main() {
  const Presonus::Panel::RogueFrontPanelComponent panel(
      Presonus::Panel::RogueFrontPanelComponent::SourcePortConstruction{});
  int group, alias;
  while (std::cin >> group >> alias) {
    const int a[] = {900, -1}, b[] = {901, -1};
    const int *first = a, *second = b;
    if (alias)
      first = b;
    int count = 77;
    if (alias) {
      panel.getTablesForGroup(group, first, first, count);
      second = first;
    } else
      panel.getTablesForGroup(group, first, second, count);
    std::cout << count;
    print(first);
    std::cout << " |";
    print(second);
    std::cout << '\n';
  }
}
