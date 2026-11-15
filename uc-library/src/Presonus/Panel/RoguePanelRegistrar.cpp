#include "presonus/panel/RoguePanelRegistrar.hpp"
namespace Presonus::Panel {
const int *RoguePanelRegistrar::getTags(int group, int &count) const {
  if (group != 20)
    return nullptr;
  count = 16;
  static constexpr int tags[] = {8, 9, 10, 11, 12, 13, 14, 15,
                                 0, 1, 2,  3,  4,  5,  6,  7};
  return tags;
}
int RoguePanelRegistrar::getParamInfoListSizeFromGroup(int group) {
  switch (group) {
  case 0:
    return 33;
  case 1:
    return 26;
  case 2:
    return 30;
  case 3:
    return 16;
  case 4:
    return 16;
  case 5:
    return 15;
  case 6:
    return 10;
  case 7:
    return 25;
  case 8:
    return 0;
  case 9:
    return 0;
  case 10:
    return 18;
  case 11:
    return 3;
  case 12:
    return 21;
  case 13:
    return 18;
  case 14:
    return 25;
  case 15:
    return 17;
  case 16:
    return 1;
  default:
    return 0;
  }
}
} // namespace Presonus::Panel
