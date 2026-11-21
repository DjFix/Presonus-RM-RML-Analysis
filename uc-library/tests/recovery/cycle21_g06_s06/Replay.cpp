#include "core/portable/coreparams.h"
#include "presonus/LPFControl.hpp"
#include <iostream>
#include <vector>

using namespace Core;
using namespace Core::Portable;

namespace {
struct Paint final : ColorBitmapRenderer {
  using ColorBitmapRenderer::ColorBitmapRenderer;
  void output(int op, RectRef r, ColorRef c) {
    const auto color = unsigned(c.red) | unsigned(c.green) << 8 |
                       unsigned(c.blue) << 16 | unsigned(c.alpha) << 24;
    std::cout << op << ' ' << r.left << ' ' << r.top << ' ' << r.right << ' '
              << r.bottom << ' ' << color << ' ';
  }
  bool fillRect(RectRef r, ColorRef c) override {
    output(1, r, c);
    return ColorBitmapRenderer::fillRect(r, c);
  }
  bool drawRect(RectRef r, ColorRef c) override {
    output(2, r, c);
    return ColorBitmapRenderer::drawRect(r, c);
  }
};
} // namespace

int main() {
  int w, h, focus, present;
  float value;
  while (std::cin >> w >> h >> focus >> present >> value) {
    Bitmap bitmap(128, 128);
    Paint graphics(bitmap);
    Style style;
    style.setBackColor(Color(1, 2, 3, 255));
    style.setTextColor(Color(7, 8, 9, 255));
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    NumericParam parameter(info);
    parameter.setNormalized(value, false);
    LPFControl view(Rect(3, 8, 3 + w, 8 + h), present ? &parameter : nullptr);
    view.wantsFocus(true);
    view.onFocus(focus != 0);
    view.setStyle(new Style(style));
    view.draw(DrawEvent(graphics, Rect(0, 0, w, h), Point()));
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
