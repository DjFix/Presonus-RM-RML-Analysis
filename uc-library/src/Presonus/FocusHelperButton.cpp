#include "presonus/FocusHelperButton.hpp"
#include <cmath>
#include <cstdint>
#include <limits>

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
void FocusHelperButton::paramChanged(Core::Portable::Parameter *p,
                                     int message) {
  Core::Portable::Control::paramChanged(p, message);
  if (message != 3)
    return;
  // The original calls ARM __aeabi_f2iz. Explicit bounds avoid undefined host
  // floating-to-integer conversion. Runtime edge behavior is validated
  // separately.
  const float input = p->getValue();
  int converted;
  if (std::isnan(input))
    converted = 0;
  else if (input >= 2147483648.0f)
    converted = std::numeric_limits<std::int32_t>::max();
  else if (input < -2147483648.0f)
    converted = std::numeric_limits<std::int32_t>::min();
  else
    converted = static_cast<std::int32_t>(input);
  if (converted == getValue())
    active_ = true;
}

void FocusHelperButton::restoreFocus() {
  active_ = false;
  auto *parent = getParent();
  if (!parent)
    return;
  // The original tests View ('View') then accesses its native child fields.
  // CCL 5.0 stores children on ContainerView. This is an intentional source
  // adaptation: a plain modern View has no children and is safely ignored.
  auto *view = Core::Portable::core_cast<Core::Portable::View>(parent);
  auto *container = view ? view->asContainer() : nullptr;
  if (!container)
    return;
  const auto &children = container->getChildren();
  const int count = children.count();
  for (int i = 0; i < count; ++i) {
    auto *child = children.at(i);
    if (child->getName() == viewName_)
      if (auto *root = getRootView())
        root->setFocusView(child);
  }
}

void FocusHelperButton::draw(const Core::Portable::DrawEvent &e) {
  Core::Portable::Button::draw(e);
  if (isOn() && isEnabled())
    Core::Portable::Control::drawFocusFrame(e);
}

void FocusHelperButton::onIdle() {
  Core::Portable::Control::onIdle();
  if (active_)
    restoreFocus();
}
} // namespace Presonus
