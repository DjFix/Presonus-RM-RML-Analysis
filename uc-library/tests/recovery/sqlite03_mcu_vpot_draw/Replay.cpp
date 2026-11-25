#include "core/portable/gui/coregraphics.h"
#include "presonus/McuVpotControl.hpp"
#include <iostream>
#include <string>
#include <vector>

using namespace Core;
using namespace Core::Portable;

namespace {
struct Renderer : ColorBitmapRenderer {
  using ColorBitmapRenderer::ColorBitmapRenderer;
  std::vector<std::string> calls;

  static std::string point(PointRef p) {
    return std::to_string(p.x) + ":" + std::to_string(p.y);
  }

  static std::string rect(RectRef r) {
    return point(r.getLeftTop()) + ":" + point(r.getRightBottom());
  }

  bool fillRect(RectRef r, ColorRef c) override {
    calls.push_back("fill:" + rect(r) + ":" + std::to_string(c));
    return ColorBitmapRenderer::fillRect(r, c);
  }

  bool drawRect(RectRef r, ColorRef c) override {
    calls.push_back("rect:" + rect(r) + ":" + std::to_string(c));
    return ColorBitmapRenderer::drawRect(r, c);
  }

  bool drawLine(PointRef a, PointRef b, ColorRef c) override {
    calls.push_back("line:" + point(a) + ":" + point(b) + ":" +
                    std::to_string(c));
    return ColorBitmapRenderer::drawLine(a, b, c);
  }

  void printAndClear() {
    std::cout << calls.size();
    for (const auto &call : calls)
      std::cout << ' ' << call;
    std::cout << '\n';
    calls.clear();
  }
};

struct ControlProbe : Presonus::McuVpotControl {
  using Presonus::McuVpotControl::isFocused;
  using Presonus::McuVpotControl::McuVpotControl;
};

struct ProviderProbe : ValueBar {
  using Control::drawFocusFrame;
  using ValueBar::drawBackground;
  using ValueBar::ValueBar;
};

Style *createStyle() {
  auto *style = new Style;
  Color color;
  color(0x78563412);
  style->setForeColor(color);
  color(0x55667788);
  style->setTextColor(color);
  color(0x11223344);
  style->setBackColor(color);
  return style;
}
} // namespace

int main() {
  int width, height;
  bool primary, enabled, vertical, disabled, focus, hasStyle, hasDot;
  float value, style, dot;
  while (std::cin >> width >> height >> primary >> enabled >> vertical >>
         disabled >> focus >> hasStyle >> hasDot >> value >> style >> dot) {
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = -1e12f;
    info.maxValue = 1e12f;
    NumericParam mainParameter(info), styleParameter(info), dotParameter(info);
    mainParameter.setValueFast(value);
    mainParameter.enable(enabled);
    styleParameter.setValueFast(style);
    dotParameter.setValueFast(dot);

    const Rect bounds(7, 9, 7 + width, 9 + height);
    ControlProbe control(bounds, primary ? &mainParameter : nullptr);
    control.setDotParameter(hasDot ? &dotParameter : nullptr);
    control.setStyleParameter(hasStyle ? &styleParameter : nullptr);
    control.isVertical(vertical);
    control.enable(!disabled);
    control.isFocused(focus);
    control.setStyle(createStyle());

    Bitmap output(140, 60);
    Renderer renderer(output);
    DrawEvent event(renderer, Rect(1, 2, width / 2 + 2, height / 2 + 3));
    View &view = control;
    view.draw(event);
    renderer.printAndClear();

    // Expand native provider boundary markers independently using the pinned
    // background and focus implementations and matching provider state.
    ProviderProbe provider(bounds, nullptr);
    provider.setStyle(createStyle());
    provider.drawBackground(event);
    renderer.printAndClear();
    provider.drawFocusFrame(event);
    renderer.printAndClear();
  }
  return std::cin.eof() ? 0 : 1;
}
