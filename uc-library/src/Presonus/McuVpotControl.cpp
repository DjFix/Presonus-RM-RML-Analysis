#include "presonus/McuVpotControl.hpp"
#include "core/portable/gui/coreviewbuilder.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace Presonus {
McuVpotControl::McuVpotControl(const Core::TRect<int> &size,
                               Core::Portable::Parameter *parameter)
    : Core::Portable::Slider(size, parameter), value_(0) {}

McuVpotControl::PortableState McuVpotControl::portableState() const {
  return {image_.getBitmap(), strip_.getBitmap(), slice_.getBitmap(), value_,
          styleParameter_,    dotParameter_};
}
namespace {
// The ARM soft-float conversion truncates in range, saturates overflow and
// maps NaN to zero. Parameter::getIntValue has no portable overflow behavior.
int truncatedValue(const Core::Portable::Parameter &parameter) {
  const double value = parameter.getValue();
  if (std::isnan(value))
    return 0;
  return static_cast<int>(std::clamp(value,
                                     double(std::numeric_limits<int>::min()),
                                     double(std::numeric_limits<int>::max())));
}
} // namespace

void McuVpotControl::draw(const Core::Portable::DrawEvent &event) {
  const auto *parameter = getParameter();
  if (!parameter || !parameter->isEnabled() || isVertical())
    return;

  drawBackground(event);
  Core::Rect client;
  getClientRect(client);

  constexpr int segmentCount = 11;
  constexpr int middle = segmentCount / 2;
  int segmentWidth = (client.getWidth() - (segmentCount - 1)) / segmentCount;
  if (segmentWidth % 2 == 0)
    --segmentWidth;
  const int step = segmentWidth + 1;
  const int centerX = client.left + client.getWidth() / 2;
  const int dotSize = (client.getHeight() - 9) / 2;

  const int style = styleParameter_ ? truncatedValue(*styleParameter_) : 2;
  const int value = truncatedValue(*parameter);
  // Very large positive ARM conversions saturate to INT_MAX. Adding the
  // midpoint then wraps to a negative value before the native clamp.
  const int position = value > std::numeric_limits<int>::max() - middle
                           ? 0
                           : std::clamp(value + middle, 0, segmentCount - 1);
  int first = 0;
  int end = 0;
  switch (style) {
  case 1:
    first = position;
    end = position + 1;
    break;
  case 2:
    end = position;
    break;
  case 3:
    if (position < middle)
      end = middle + 1;
    else {
      first = middle;
      end = position + 1;
    }
    break;
  }

  const auto &color = getStyle().getForeColor();
  const int halfSegment = segmentWidth / 2;
  const int left = centerX - halfSegment - middle * step;
  for (int segment = first; segment < end; ++segment) {
    const int x = left + segment * step;
    event.graphics.fillRect(
        Core::Rect(x, 3, x + 2 * halfSegment + 1, dotSize + 3), color);
  }

  if (dotParameter_ && truncatedValue(*dotParameter_) != 0) {
    const int halfDot = dotSize / 2;
    const int top = dotSize + 6;
    event.graphics.fillRect(Core::Rect(centerX - halfDot, top,
                                       centerX + halfDot + 1, top + dotSize),
                            color);
  }
  event.graphics.drawLine(Core::Point(centerX, 1),
                          Core::Point(centerX, client.bottom - 1), color);
  if (isFocused())
    drawFocusFrame(event);
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
