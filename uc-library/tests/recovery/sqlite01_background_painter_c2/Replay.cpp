#include "core/portable/gui/coregraphics.h"
#include "presonus/BackgroundPainter.hpp"
#include <cstdint>
#include <iostream>

namespace {
using namespace Core;
using namespace Core::Portable;

struct Renderer : ColorBitmapRenderer {
  using ColorBitmapRenderer::ColorBitmapRenderer;
  Rect filled;
  Color color;
  int calls = 0;

  bool fillRect(RectRef rectangle, ColorRef value) override {
    ++calls;
    filled = rectangle;
    color = value;
    return ColorBitmapRenderer::fillRect(rectangle, value);
  }
};

[[gnu::noinline]] void dispatch(Presonus::BackgroundPainter &painter,
                                RectRef rectangle, const DrawEvent &event,
                                const Style &style) {
  painter.paint(rectangle, event, style);
}
} // namespace

struct Derived final : Presonus::BackgroundPainter {
  explicit Derived(bool &destroyed) : destroyed(destroyed) {}
  ~Derived() override { destroyed = true; }
  bool &destroyed;
};

int main() {
  Bitmap bitmap(12, 12, kBitmapRGBAlpha);
  Renderer renderer(bitmap);
  const Rect update(1, 2, 7, 8);
  const DrawEvent event(renderer, update, Point());
  Style style;
  const Color color(12, 35, 91, 255);
  style.setBackColor(color);
  bool destroyed = false;
  {
    struct {
      std::uint64_t before = 0xEF129012273F5AA7;
      Derived painter;
      std::uint64_t after = 0xA5E9D55530BA29CC;
    } guarded{0xEF129012273F5AA7, Derived(destroyed), 0xA5E9D55530BA29CC};
    dispatch(guarded.painter, Rect(0, 0, 12, 12), event, style);
    if (renderer.calls != 1 || renderer.filled != update ||
        uint32(renderer.color) != uint32(color) ||
        guarded.before != 0xEF129012273F5AA7 ||
        guarded.after != 0xA5E9D55530BA29CC)
      return 1;
  }
  if (!destroyed)
    return 1;
  std::cout << "1 portable base-constructor paint dispatch and derived "
               "lifetime passed\n";
}
