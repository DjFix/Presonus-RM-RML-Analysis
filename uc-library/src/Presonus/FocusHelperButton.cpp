#include "presonus/FocusHelperButton.hpp"

namespace Presonus {
FocusHelperButton::FocusHelperButton(const Core::TRect<int> &size,
                                     Core::Portable::Parameter *parameter,
                                     int value)
    : Core::Portable::RadioButton(size, parameter, value), active_(false),
      viewName_("") {}

void FocusHelperButton::setAttributes(const Core::Portable::Attributes &a) {
  Core::Portable::RadioButton::setAttributes(a);
  const char *name = a.getString("viewName");
  viewName_ = name ? name : "";
}
} // namespace Presonus
