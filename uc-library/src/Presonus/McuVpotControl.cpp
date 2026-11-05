#include "presonus/McuVpotControl.hpp"
#include "core/portable/gui/coreviewbuilder.h"

namespace Presonus {
McuVpotControl::McuVpotControl(const Core::TRect<int> &size,
                               Core::Portable::Parameter *parameter)
    : Core::Portable::Slider(size, parameter), value_(0) {}

McuVpotControl::PortableState McuVpotControl::portableState() const {
  return {image_.getBitmap(), strip_.getBitmap(), slice_.getBitmap(), value_,
          styleParameter_,    dotParameter_};
}
void McuVpotControl::setAttributes(const Core::Portable::Attributes &a) {
  Core::Portable::ValueBar::setAttributes(a);
  auto *controller =
      portableController_
          ? portableController_
          : Core::Portable::ViewBuilder::instance().getCurrentController();
  const auto *styleName = a.getString("valuestyle");
  if (styleName && *styleName && controller)
    setStyleParameter(static_cast<Core::Portable::Parameter *>(
        controller->getObjectForView(styleName, Core::Portable::kParamType)));
  const auto *dotName = a.getString("dot");
  if (dotName && *dotName && controller)
    setDotParameter(static_cast<Core::Portable::Parameter *>(
        controller->getObjectForView(dotName, Core::Portable::kParamType)));
  image_ = Core::Portable::ViewAttributes::getBitmap(a, "image");
}
McuVpotControl::~McuVpotControl() {
  if (styleParameter_)
    styleParameter_->removeObserver(this);
  if (dotParameter_)
    dotParameter_->removeObserver(this);
}
void McuVpotControl::paramChanged(Core::Portable::Parameter *p, int message) {
  if (message == Core::Portable::Parameter::kChanged) {
    if (p == styleParameter_ || p == dotParameter_)
      invalidate();
  } else if (message == Core::Portable::Parameter::kDestroyed) {
    if (p == styleParameter_)
      styleParameter_ = nullptr;
    if (p == dotParameter_)
      dotParameter_ = nullptr;
  }
  // Pinned CCL asserts on kDestroyed in debug builds. Retain its source
  // behavior; this port does not claim firmware provider equivalence for
  // destruction.
  Core::Portable::Control::paramChanged(p, message);
}
void McuVpotControl::setDotParameter(Core::Portable::Parameter *p) {
  if (dotParameter_ == p)
    return;
  if (dotParameter_)
    dotParameter_->removeObserver(this);
  dotParameter_ = p;
  if (dotParameter_)
    dotParameter_->addObserver(this);
  invalidate();
}
void McuVpotControl::setStyleParameter(Core::Portable::Parameter *p) {
  if (styleParameter_ == p)
    return;
  if (styleParameter_)
    styleParameter_->removeObserver(this);
  styleParameter_ = p;
  if (styleParameter_)
    styleParameter_->addObserver(this);
  invalidate();
}
} // namespace Presonus
