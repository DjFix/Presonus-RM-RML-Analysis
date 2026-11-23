#include "core/portable/coreattributes.h"
#include "core/portable/gui/coregraphics.h"
#include "core/public/coreinterpolator.h"
#include "presonus/MeterScaleControl.hpp"
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>

namespace presonus::meter {
struct MeterScaleAttributeAccess {
  static auto range(const Presonus::MeterScaleControl &control) {
    return control.range_;
  }
  static auto scale(const Presonus::MeterScaleControl &control) {
    return control.scale_.get();
  }
};
} // namespace presonus::meter

using presonus::meter::MeterScaleAttributeAccess;

class ObservedControl : public Presonus::MeterScaleControl {
public:
  using MeterScaleControl::MeterScaleControl;

  void setSize(Core::RectRef rect) override {
    resolvedBeforeBase =
        expectedRange != MeterScaleAttributeAccess::range(*this) ||
        expectedScale != MeterScaleAttributeAccess::scale(*this);
    ++sizeCalls;
    Core::Portable::View::setSize(rect);
  }

  const Ranges::Range *expectedRange = nullptr;
  const Core::Interpolator *expectedScale = nullptr;
  bool resolvedBeforeBase = false;
  int sizeCalls = 0;
};

class TickRecorder : public Core::Portable::Graphics {
public:
  bool setOrigin(Core::PointRef) override { return true; }
  bool setClip(Core::RectRef) override { return true; }
  int setMode(int mode) override { return mode; }
  bool fillRect(Core::RectRef, Core::ColorRef) override { return true; }
  bool drawRect(Core::RectRef, Core::ColorRef) override { return true; }
  bool drawLinearGradient(Core::PointRef, Core::PointRef, Core::ColorRef,
                          Core::ColorRef, Direction) override {
    return true;
  }
  bool drawLine(Core::PointRef, Core::PointRef, Core::ColorRef) override {
    return true;
  }
  bool drawString(Core::RectRef, Core::CStringPtr text, Core::ColorRef,
                  Core::CStringPtr, int) override {
    ticks.push_back(std::stoi(text));
    return true;
  }
  bool drawMultiLineString(Core::RectRef, Core::CStringPtr, Core::ColorRef,
                           Core::CStringPtr, int) override {
    return true;
  }
  int getStringWidth(Core::CStringPtr, Core::CStringPtr) const override {
    return 0;
  }
  bool drawBitmap(Core::PointRef, Core::Portable::Bitmap &, Core::RectRef,
                  const Core::Portable::BitmapMode *) override {
    return true;
  }
  const Core::Portable::BitmapFont *getFont(Core::CStringPtr) const override {
    return nullptr;
  }

  std::vector<int> ticks;
};

static void setAttribute(Core::Portable::Attributes &attrs, const char *key) {
  char type;
  std::cin >> type;
  if (type == 's') {
    std::string value;
    std::cin >> std::quoted(value);
    attrs.set(key, value.c_str());
  } else if (type == 'i') {
    int value;
    std::cin >> value;
    attrs.set(key, value);
  }
}

int main() {
  ObservedControl control(Core::Rect(2, 3, 4, 5));
  Core::Portable::View reference(Core::Rect(2, 3, 4, 5));
  bool initialized = false;
  for (int warm, count = 0; std::cin >> warm; ++count) {
    if (warm && !initialized) {
      __initMeterScaleControl();
      initialized = true;
    }

    Core::Portable::Attributes attrs(
        Core::Portable::AttributeAllocator::getDefault());
    setAttribute(attrs, "range");
    setAttribute(attrs, "interpolator");
    attrs.set("width", 123 + count);
    attrs.set("height", 234 + count);
    reference.setAttributes(attrs);
    control.expectedRange = MeterScaleAttributeAccess::range(control);
    control.expectedScale = MeterScaleAttributeAccess::scale(control);
    control.sizeCalls = 0;
    Core::Portable::View &view = control;
    view.setAttributes(attrs);
    if (control.sizeCalls != 1 || control.getSize() != reference.getSize() ||
        control.getSize().getWidth() != 123 + count ||
        control.getSize().getHeight() != 234 + count ||
        control.resolvedBeforeBase)
      return 1;

    const auto *range = MeterScaleAttributeAccess::range(control);
    const auto *scale = MeterScaleAttributeAccess::scale(control);
    std::unique_ptr<Core::Interpolator> direct(
        Core::InterpolatorFactory::create(attrs.getString("interpolator")));
    if (bool(scale) != bool(direct))
      return 2;

    std::cout << (range ? range->name.str() : "-") << ' '
              << (scale ? scale->getName() : "-");
    if (scale) {
      if (range)
        direct->setRange(static_cast<float>(range->values[0]),
                         static_cast<float>(range->values[range->count - 1]),
                         1.f);
      if (scale->rangeToNormalized(scale->getMinRange()) !=
              direct->rangeToNormalized(direct->getMinRange()) ||
          scale->normalizedToRange(0.25f) != direct->normalizedToRange(0.25f))
        return 3;
      std::cout << ' ' << scale->getMinRange() << ' ' << scale->getMaxRange()
                << ' ' << scale->getMidRange();
    }
    TickRecorder graphics;
    control.draw(Core::Portable::DrawEvent(graphics, control.getSize()));
    std::cout << " |";
    for (int tick : graphics.ticks)
      std::cout << ' ' << tick;
    std::cout << '\n';
    if (range) {
      graphics.ticks.clear();
      control.setPortableScaleTicks({-22, -11});
      control.draw(Core::Portable::DrawEvent(graphics, control.getSize()));
      if (graphics.ticks != std::vector<int>{-22, -11})
        return 4;
      control.setPortableScaleTicks({});
    }
  }
}
