#include "presonus/MeterScaleControl.hpp"
#include "core/portable/coreattributes.h"
#include "core/portable/gui/corefont.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corestringbuffer.h"
#include "presonus/MeterControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/MuteGroupsComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iterator>
#include <stdexcept>
#include <type_traits>

namespace {
Presonus::MeterScaleControl::Ranges &meterScaleRanges() {
  using Ranges = Presonus::MeterScaleControl::Ranges;
  static Ranges ranges(Ranges::SourcePortTag{});
  return ranges;
}
} // namespace

namespace Presonus {
MeterScaleControl::MeterScaleControl(const Core::Rect &rect)
    : Core::Portable::Control(rect, nullptr) {}
MeterScaleControl::~MeterScaleControl() = default;
MeterScaleControl::Ranges::~Ranges() {
  for (int i = 0; i < values_.count(); ++i)
    ::operator delete(values_.at(i));
}
void MeterScaleControl::Ranges::addRange(const char *name, int count,
                                         const int *values) {
  static_assert(std::is_trivially_destructible_v<Range>);
  auto record = std::unique_ptr<Range>(new Range{values, count, {name}});
  // The temporary owner cleans up if the provider cannot grow the vector.
  if (values_.add(record.get()))
    record.release();
}

MeterScaleControl::Ranges::Range *
MeterScaleControl::Ranges::getRange(const char *name) {
  const char *key = name ? name : "";
  for (int i = 0; i < values_.count(); ++i) {
    auto *record = values_.at(i);
    if (std::strcmp(record->name.str(), key) == 0)
      return record;
  }
  return nullptr;
}

void MeterScaleControl::setAttributes(
    const Core::Portable::Attributes &attributes) {
  Core::Portable::View::setAttributes(attributes);
  const auto *rangeName = attributes.getString("range");
  range_ = meterScaleRanges().getRange(rangeName ? rangeName : "");
  scale_.reset(
      Core::InterpolatorFactory::create(attributes.getString("interpolator")));
  if (scale_ && range_)
    scale_->setRange(static_cast<float>(range_->values[0]),
                     static_cast<float>(range_->values[range_->count - 1]),
                     1.f);
}

void MeterScaleControl::draw(const Core::Portable::DrawEvent &event) {
  const int *values = ticks_.data();
  std::size_t count = ticks_.size();
  if (count == 0 && range_) {
    values = range_->values;
    count = static_cast<std::size_t>(range_->count);
  }
  if (count == 0)
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
  const int first = values[0];
  const float span = static_cast<float>(
      std::abs(static_cast<long long>(values[count - 1]) - first));
  const float inverseSpan = span == 0 ? 0.f : 1.f / span;
  for (std::size_t i = 0; i < count; ++i) {
    const int value = values[i];
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

void __initMeterScaleControl() {
  static constexpr int defaultValues[] = {-84, -72, -60, -48, -36,
                                          -24, -12, 0,   10};
  static constexpr int recordArmedValues[] = {-60, -48, -36, -24, -12,
                                              -9,  -6,  -3,  0};
  static constexpr int outputValues[] = {-60, -48, -36, -24, -12, -9,
                                         -6,  -3,  0,   3,   6};
  auto &ranges = meterScaleRanges();
  ranges.addRange("default", std::size(defaultValues), defaultValues);
  ranges.addRange("recordArmed", std::size(recordArmedValues),
                  recordArmedValues);
  ranges.addRange("output", std::size(outputValues), outputValues);
}

const Presonus::MeterScaleControl::Ranges &
presonus::meter::sourcePortMeterScaleRanges() {
  return meterScaleRanges();
}
