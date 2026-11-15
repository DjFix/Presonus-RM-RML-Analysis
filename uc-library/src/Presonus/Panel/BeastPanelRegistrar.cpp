#include "presonus/panel/BeastPanelRegistrar.hpp"
#include "presonus/panel/PanelParameterTables.hpp"

namespace {
// Exact 32 words observed at 0x34fc54 in RM/RML mixer 13731. This
// private portable table does not claim the original data declaration.
constexpr std::int32_t tags[] = {20, 21, 22, 23, -1, -1, -1, -1, 12, 13, 14,
                                 15, 16, 17, 18, 19, 8,  9,  10, 11, -1, -1,
                                 -1, -1, 0,  1,  2,  3,  4,  5,  6,  7};
} // namespace

namespace Presonus::Panel {
const std::int32_t *BeastPanelRegistrar::getTags(int group, int &count) const {
  if (group != 20)
    return nullptr;
  count = 32;
  return tags;
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
int BeastPanelRegistrar::getParamInfoListSizeFromGroup(int group) {
  constexpr int counts[] = {45, 38, 42, 24, 24, 15, 14, 26, 0,
                            0,  18, 3,  29, 26, 33, 21, 1};
  return static_cast<unsigned>(group) < 17 ? counts[group] : 0;
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
const Core::Portable::ParamInfo *
BeastPanelRegistrar::getParamInfoListFromGroup(int group) {
  switch (group) {
  case 0:
    return presonus::panel::panelParameterTable(0x34ba0c);
  case 1:
    return presonus::panel::panelParameterTable(0x348e68);
  case 2:
    return presonus::panel::panelParameterTable(0x349ae0);
  case 3:
    return presonus::panel::panelParameterTable(0x348688);
  case 4:
    return presonus::panel::panelParameterTable(0x34b22c);
  case 5:
    return presonus::panel::panelParameterTable(0x34ceb8);
  case 6:
    return presonus::panel::panelParameterTable(0x34d3a4);
  case 7:
    return presonus::panel::panelParameterTable(0x34a8a8);
  case 10:
    return presonus::panel::panelParameterTable(0x34c8d0);
  case 11:
    return presonus::panel::panelParameterTable(0x34b130);
  case 12:
    return presonus::panel::panelParameterTable(0x34d83c);
  case 13:
    return presonus::panel::panelParameterTable(0x34e8a4);
  case 14:
    return presonus::panel::panelParameterTable(0x34f12c);
  case 15:
    return presonus::panel::panelParameterTable(0x34e1c0);
  case 16:
    return presonus::panel::panelParameterTable(0x34fc00);
  default:
    return nullptr;
  }
}
} // namespace Presonus::Panel
