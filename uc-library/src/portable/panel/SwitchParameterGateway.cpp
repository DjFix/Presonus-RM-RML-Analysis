#include "presonus/panel/switch_control.hpp"

namespace presonus::panel_binding {
void resetSwitchParameter(Core::Portable::Parameter &parameter) {
  parameter.resetValue(false);
}
} // namespace presonus::panel_binding
