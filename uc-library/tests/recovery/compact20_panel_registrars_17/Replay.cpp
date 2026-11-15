#include "presonus/panel/RoguePanelRegistrar.hpp"
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int group = std::atoi(argv[1]);
  Presonus::Panel::RoguePanelRegistrar object;
  std::cout << object.getParamInfoListSizeFromGroup(group);
  std::cout << "\n";
}
