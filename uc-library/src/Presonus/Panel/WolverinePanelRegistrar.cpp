#include "presonus/panel/WolverinePanelRegistrar.hpp"
#include "presonus/panel/PanelParameterTables.hpp"
namespace Presonus::Panel {
int WolverinePanelRegistrar::getParamInfoListSizeFromGroup(int group) {
  static constexpr int counts[16] = {102, 32, 0, 32, 0, 0, 0, 0,
                                     0,   0,  0, 0,  0, 0, 0, 1};
  return static_cast<unsigned>(group) < 16 ? counts[group] : 0;
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
const Core::Portable::ParamInfo *
WolverinePanelRegistrar::getParamInfoListFromGroup(int group) {
  switch (group) {
  case 0:
    return presonus::panel::panelParameterTable(0x350cdc);
  case 1:
    return presonus::panel::panelParameterTable(0x352e54);
  case 3:
    return presonus::panel::panelParameterTable(0x350208);
  case 15:
    return presonus::panel::panelParameterTable(0x350c88);
  default:
    return nullptr;
  }
}
} // namespace Presonus::Panel
