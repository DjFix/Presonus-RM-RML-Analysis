#include "presonus/surface_panel/ControlHelpers.hpp"

namespace Presonus::Surface {
int PanelRegistrar::getFaderSensitivity() {
  return static_cast<int>(parameters_->byTag(901)->getValue());
}
int PanelRegistrar::getFaderSpeed() {
  return static_cast<int>(parameters_->byTag(900)->getValue());
}
} // namespace Presonus::Surface
