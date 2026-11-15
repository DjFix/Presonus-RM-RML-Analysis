#include "presonus/panel/StormPanelRegistrar.hpp"
namespace Presonus::Panel {
const int *StormPanelRegistrar::getTags(int group, int &count) const {
  if (group != 20)
    return nullptr;
  count = 40;
  static constexpr int tags[] = {28, 29, 30, 31, -1, -1, -1, -1, 20, 21,
                                 22, 23, 24, 25, 26, 27, 12, 13, 14, 15,
                                 16, 17, 18, 19, 8,  9,  10, 11, -1, -1,
                                 -1, -1, 0,  1,  2,  3,  4,  5,  6,  7};
  return tags;
}
int StormPanelRegistrar::getParamInfoListSizeFromGroup(int group) {
  switch (group) {
  case 0:
    return 57;
  case 1:
    return 50;
  case 2:
    return 54;
  case 3:
    return 32;
  case 4:
    return 32;
  case 5:
    return 15;
  case 6:
    return 18;
  case 7:
    return 26;
  case 8:
    return 8;
  case 9:
    return 8;
  case 10:
    return 18;
  case 11:
    return 3;
  case 12:
    return 37;
  case 13:
    return 34;
  case 14:
    return 41;
  case 15:
    return 25;
  case 16:
    return 1;
  default:
    return 0;
  }
}
} // namespace Presonus::Panel
