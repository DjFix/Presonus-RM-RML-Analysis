#include "core/portable/gui/corefont.h"
#include "presonus/MeterScaleControl.hpp"
#include <iostream>
#include <memory>
#include <string_view>
#include <vector>

using namespace Core;
using namespace Core::Portable;

namespace {
struct FixtureFont : BitmapFont {
  FixtureFont() : BitmapFont("fixture", nullptr, false) {}
  void setHeight(int value) { lineHeight = value; }
};

struct Paint : ColorBitmapRenderer {
  using ColorBitmapRenderer::ColorBitmapRenderer;
  FixtureFont font;
  bool hasFont{};

  static void prefix(int operation, ColorRef c) {
    std::cout << operation << ' ' << uint32(c) << ' ';
  }
  static void rect(RectRef r) {
    std::cout << r.left << ' ' << r.top << ' ' << r.right << ' ' << r.bottom
              << ' ';
  }
  bool fillRect(RectRef r, ColorRef c) override {
    prefix(1, c);
    rect(r);
    return ColorBitmapRenderer::fillRect(r, c);
  }
  bool drawLine(PointRef a, PointRef b, ColorRef c) override {
    prefix(2, c);
    std::cout << a.x << ' ' << a.y << ' ' << b.x << ' ' << b.y << ' ';
    return ColorBitmapRenderer::drawLine(a, b, c);
  }
  bool drawString(RectRef r, CStringPtr text, ColorRef color,
                  CStringPtr fontName, int alignment) override {
    prefix(3, color);
    rect(r);
    std::cout << alignment << ' ';
    for (const char *p = text; *p; ++p)
      std::cout << int(*p) << ' ';
    std::cout << 0 << ' ';
    return std::string_view(fontName) == "fixture";
  }
  const BitmapFont *getFont(CStringPtr name) const override {
    const bool matched = std::string_view(name) == "fixture";
    std::cout << 4 << ' ' << matched << ' ';
    return hasFont && matched ? &font : nullptr;
  }
};
} // namespace

int main() {
  constexpr SegmentInterpolator::BreakPoint points[] = {
      {0.f, -60.f}, {0.25f, -30.f}, {1.f, 0.f}};
  int w, h, fontHeight, scale, count;
  while (std::cin >> w >> h >> fontHeight >> scale >> count) {
    std::vector<int> ticks;
    for (int i = 0; i < count; ++i) {
      int value;
      if (!(std::cin >> value))
        return 1;
      ticks.push_back(value);
    }
    Bitmap bitmap(128, 128);
    Paint graphics(bitmap);
    graphics.hasFont = fontHeight >= 0;
    graphics.font.setHeight(fontHeight);
    auto *style = new Style;
    style->setBackColor(Color(1, 2, 3, 255));
    style->setForeColor(Color(7, 8, 9, 255));
    style->setForeColorDisabled(Color(17, 18, 19, 255));
    style->setTextAlign(5);
    style->setFontName("fixture");
    Presonus::MeterScaleControl view(Rect(0, 0, w, h));
    view.setStyle(style);
    view.setPortableScaleTicks(std::move(ticks));
    if (scale)
      view.adoptScaleInterpolator(
          std::make_unique<SegmentInterpolator>(3, points));
    view.draw(DrawEvent(graphics, Rect(1, 2, w - 1, h - 2)));
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
