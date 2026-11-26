#include "presonus/SpectrumPainter.hpp"

#include <algorithm>
#include <cmath>

namespace Presonus {
namespace {

constexpr float minimumAmplitude = 6.309573308271865e-08f;
constexpr float floorDecibels = -144.f;
constexpr float referenceDecibels = -40.f;
constexpr float displayRange = 40.f;
constexpr float alternatingShade = 2.55f;

} // namespace

SpectrumPainter::SpectrumPainter(IBackgroundGridProvider &grid)
    : grid_(&grid) {}

void SpectrumPainter::setData(const float *amplitudes, int count,
                              const float *frequencies) {
  amplitudes_ = amplitudes;
  frequencies_ = frequencies;
  count_ = count;
  bars_.removeAll();
  for (int i = 0; i < count_; ++i)
    bars_.add(Bar{});
  initialized_ = false;
}

void SpectrumPainter::init(const Core::TRect<int> &bounds) {
  if (count_ <= 0 || !frequencies_ || !grid_)
    return;
  initialized_ = true;
  if (count_ != bars_.count())
    return;

  const int height = bounds.getHeight();
  for (int i = 0; i < count_; ++i) {
    auto &bar = bars_.at(i);
    bar.center = grid_->toXGridPixel(frequencies_[i]);
    bar.rect.top = height;
    bar.rect.bottom = height;
  }
  if (count_ == 1) {
    auto &bar = bars_.first();
    // The native resize initializes the next backing entry's center to zero.
    bar.rect.left = 0;
    bar.rect.right = bar.center - bar.center / 2;
    return;
  }

  int left = 0;
  for (int i = 0; i < count_; ++i) {
    auto &bar = bars_.at(i);
    const int right =
        i + 1 < count_ ? bar.center + (bars_.at(i + 1).center - bar.center) / 2
                       : bounds.getWidth();
    bar.rect.left = left;
    bar.rect.right = right;
    left = right;
  }
}

Core::TRect<int>
SpectrumPainter::calculateBars(const Core::TRect<int> &bounds) {
  if (!initialized_)
    init(bounds);

  if (!amplitudes_ || count_ <= 0 || count_ != bars_.count())
    return {};

  const int height = bounds.getHeight();
  int minTop = height;
  bool changed = false;
  for (int i = 0; i < count_; ++i) {
    auto &bar = bars_.at(i);
    const float amplitude = amplitudes_[i];
    if (amplitude != bar.previousAmplitude)
      bar.decibels = amplitude < minimumAmplitude
                         ? floorDecibels
                         : std::log10(amplitude) * 20.f;

    const int top =
        bar.decibels > referenceDecibels
            ? static_cast<int>(
                  (1.f - (bar.decibels - referenceDecibels) / displayRange) *
                  static_cast<float>(height))
            : bar.rect.bottom;
    changed |= bar.rect.top != top;
    bar.rect.top = top;
    minTop = std::min(minTop, top);
  }

  if (changed)
    return {bars_.first().rect.left, minTop, bars_.last().rect.right, height};
  return {};
}

Core::TRect<int>
SpectrumPainter::calculateNextDrawRect(const Core::TRect<int> &bounds) {
  next_ = calculateBars(bounds);
  next_.offset(bounds.left, bounds.top);
  return next_;
}

void SpectrumPainter::paint(const Core::TRect<int> &,
                            const Core::Portable::DrawEvent &event,
                            const Core::Portable::Style &style) {
  const auto color = style.getTextColor();
  const Core::Color shaded(Core::Color::setC(color.red - alternatingShade),
                           Core::Color::setC(color.green - alternatingShade),
                           Core::Color::setC(color.blue - alternatingShade),
                           color.alpha);
  for (int i = 0; i < bars_.count(); ++i) {
    auto rectangle = bars_.at(i).rect;
    if (rectangle.bound(event.updateRect))
      event.graphics.fillRect(rectangle, i % 2 == 0 ? color : shaded);
  }
  last_ = next_;
}

Core::TRect<int> SpectrumPainter::getLastDrawnRect() const {
  return borrowedLast_ ? *borrowedLast_ : last_;
}

} // namespace Presonus
