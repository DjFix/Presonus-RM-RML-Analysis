#include "presonus/MeterScaleControl.hpp"
#include "core/portable/gui/corefont.h"
#include "core/public/corestringbuffer.h"
#include "presonus/MeterControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/MuteGroupsComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace Presonus {
MeterScaleControl::MeterScaleControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
MeterScaleControl::~MeterScaleControl() = default;
MeterScaleControl::Ranges::~Ranges() {
  for (int i = 0; i < values_.count(); ++i)
    ::operator delete(values_.at(i));
}
void MeterScaleControl::draw(const Core::Portable::DrawEvent &event) {
  if (ticks_.empty())
    return;

  Core::Rect client;
  getClientRect(client);
  const auto &style = getStyle();
  auto &graphics = event.graphics;
  graphics.fillRect(event.updateRect, style.getBackColor());
  const auto &fontName = style.getFontName();
  const auto *font = graphics.getFont(fontName);
  const int fontHeight = font ? font->getLineHeight() : 0;
  const int height = client.getHeight();
  if (height == 0)
    return;
  const int trackHeight = static_cast<int>(
      height * (1.f - static_cast<float>(fontHeight) / height));
  const int margin = (height - trackHeight) / 2;
  const int halfFont = fontHeight / 2;
  const int width = client.getWidth();
  const int first = ticks_.front();
  const float span = static_cast<float>(
      std::abs(static_cast<long long>(ticks_.back()) - first));
  const float inverseSpan = span == 0 ? 0.f : 1.f / span;
  for (const int value : ticks_) {
    const float position =
        scale_ ? scale_->rangeToNormalized(static_cast<float>(value))
               : std::clamp(
                     static_cast<float>(static_cast<long long>(value) - first) *
                         inverseSpan,
                     0.f, 1.f);
    const int y =
        margin + ((!scale_ && span == 0)
                      ? 0
                      : static_cast<int>((1.f - position) * trackHeight));
    // Legacy color offsets are bound by role to the current style.
    const auto &color =
        value == 0 ? style.getForeColorDisabled() : style.getForeColor();
    Core::CStringBuffer<16> label;
    label.appendFormat("%i ", value);
    graphics.drawString(Core::Rect(0, y - halfFont, width, y + halfFont), label,
                        color, fontName, style.getTextAlign());
    graphics.drawLine(Core::Point(0, y), Core::Point(width / 2 - 2, y), color);
  }
}
} // namespace Presonus
