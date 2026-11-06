#include "presonus/GridPainter.hpp"
namespace Presonus {
void GridPainter::setGridOrientation(Axis axis, LabelOrientation orientation,
                                     const char *formatterName) {
  auto &selected = static_cast<int>(axis) == 0 ? first_ : second_;
  selected.orientation = static_cast<int>(orientation);
  selected.formatter = Core::FormatterRegistry::find(formatterName);
}
} // namespace Presonus
