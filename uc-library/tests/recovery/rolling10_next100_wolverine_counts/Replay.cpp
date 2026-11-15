#include "presonus/panel/WolverinePanelRegistrar.hpp"
#include <iostream>
int main() {
  Presonus::Panel::WolverinePanelRegistrar registrar;
  int group;
  while (std::cin >> group)
    std::cout << registrar.getParamInfoListSizeFromGroup(group) << '\n';
}
