#include "core/system/coredebug.h"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/PanelComponent.hpp"

namespace Presonus {
Core::Portable::Parameter *
MappingTable::getHardwareParameter(const char *name) const {
  auto *item = findItem(name);
  return item ? extended().parameter(*item) : nullptr;
}
} // namespace Presonus
namespace Presonus::Panel {
int PanelComponent::runTests(int, int, char **) {
  Core::DebugPrintf(
      "A class that inherits PanelComponent didn't implement runTests(...)\n");
  return 0;
}
} // namespace Presonus::Panel
#include "presonus/rank20cycle01/rank20c01_w06.hpp"
namespace Presonus {
void GridPainter::setGridOrientation(Axis axis, LabelOrientation orientation,
                                     const char *formatterName) {
  auto &selected = static_cast<int>(axis) == 0 ? first_ : second_;
  selected.orientation = static_cast<int>(orientation);
  selected.formatter = Core::FormatterRegistry::find(formatterName);
}
} // namespace Presonus
