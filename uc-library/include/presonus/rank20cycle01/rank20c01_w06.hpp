#pragma once
#include "core/public/coreformatter.h"
namespace presonus::grid_port {
// Explicit independent source-port storage, not original ARM class fields.
struct AxisState {
  int orientation = 0;
  const Core::Formatter *formatter = nullptr;
};
} // namespace presonus::grid_port
namespace Presonus {
// Portable source port; original layout, inheritance, return and enum
// enumerator declarations remain unresolved. Numeric zero selects the first
// axis; other bit patterns select the second, as observed in the original ARM
// body.
class GridPainter {
public:
  enum Axis : int {};
  enum LabelOrientation : int {};
  GridPainter(presonus::grid_port::AxisState &first,
              presonus::grid_port::AxisState &second)
      : first_(first), second_(second) {}
  void setGridOrientation(Axis, LabelOrientation, const char *);

private:
  presonus::grid_port::AxisState &first_;
  presonus::grid_port::AxisState &second_;
};
} // namespace Presonus
