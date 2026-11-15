#include "presonus/panel/GambitPanelRegistrar.hpp"
namespace Presonus::Panel {
int GambitPanelRegistrar::getParamInfoListSizeFromGroup(int group) {
  switch (group) {
  case 0:
    return 54;
  case 1:
    return 16;
  case 2:
    return 0;
  case 3:
    return 16;
  case 4:
    return 0;
  case 5:
    return 0;
  case 6:
    return 0;
  case 7:
    return 0;
  case 8:
    return 0;
  case 9:
    return 0;
  case 10:
    return 0;
  case 11:
    return 0;
  case 12:
    return 0;
  case 13:
    return 0;
  case 14:
    return 0;
  case 15:
    return 1;
  default:
    return 0;
  }
}
} // namespace Presonus::Panel
