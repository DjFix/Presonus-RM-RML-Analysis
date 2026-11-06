#include "presonus/BackgroundPainter.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <cassert>
#include <iostream>
#include <vector>
using namespace Core;
using namespace Core::Portable;
namespace {
using Trace = std::vector<std::vector<long long>>;
struct Renderer : ColorBitmapRenderer {
  Trace trace;
  Bitmap *images[3]{};
  bool curve = false;
  explicit Renderer(Bitmap &b) : ColorBitmapRenderer(b) {}
  bool fillRect(RectRef r, ColorRef c) override {
    trace.push_back({1, r.left, r.top, r.right, r.bottom, uint32(c)});
    return ColorBitmapRenderer::fillRect(r, c);
  }
  bool drawBitmap(PointRef p, Bitmap &b, RectRef r,
                  const BitmapMode *m = nullptr) override {
    int id = -1;
    for (int i = 0; i < 3; ++i)
      if (&b == images[i])
        id = i;
    assert(id >= 0);
    trace.push_back({2, id, p.x, p.y, r.left, r.top, r.right, r.bottom});
    return ColorBitmapRenderer::drawBitmap(p, b, r, m);
  }
  bool drawLine(PointRef a, PointRef b, ColorRef c) override {
    if (!curve)
      trace.push_back({3, uint32(c)});
    curve = true;
    return ColorBitmapRenderer::drawLine(a, b, c);
  }
};
struct Painter : Presonus::BackgroundPainter {
  Renderer &renderer;
  int id;
  Painter(Renderer &renderer, int id) : renderer(renderer), id(id) {}
  void paint(RectRef r, const DrawEvent &e, const Style &s) override {
    assert(r == Rect(3, 4, 27, 24));
    assert(&e.graphics == &renderer && uint32(s.getBackColor()) == 0xff102030u);
    renderer.trace.push_back({4, id});
  }
};
void pixels() {
  Bitmap canvas(8, 8, kBitmapRGBAlpha, 0);
  ColorBitmapRenderer g(canvas);
  g.fillRect(Rect(0, 0, 8, 8), Color(0, 0, 0));
  g.setClip(Rect(2, 3, 5, 6));
  Style style;
  style.setBackColor(Color(23, 45, 67));
  Presonus::BackgroundPainter painter;
  painter.paint(Rect(99, 99, 100, 100), DrawEvent(g, Rect(2, 3, 5, 6)), style);
  for (int y = 0; y < 8; ++y)
    for (int x = 0; x < 8; ++x) {
      auto expected = x >= 2 && x < 5 && y >= 3 && y < 6 ? style.getBackColor()
                                                         : Color(0, 0, 0);
      auto actual = canvas.accessForRead().rgbaAt(x, y);
      assert(actual.red == expected.red && actual.green == expected.green &&
             actual.blue == expected.blue && actual.alpha == expected.alpha);
    }
}
} // namespace
int main() {
  pixels();
  int mode, primary, frames, selected, enabled, on, painters, bg, clip, custom,
      base;
  while (std::cin >> mode >> primary >> frames >> selected >> enabled >> on >>
         painters >> bg >> clip >> custom >> base) {
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    info.defaultValue = 0;
    info.midValue = 1;
    NumericParam p(info), sel(info), active(info);
    p.setValue(primary > 0 ? 1.f : 0.f);
    sel.setValue(selected > 0 ? 1.f : 0.f);
    active.setValue(float(on));
    Bitmap canvas(24, 20, kBitmapRGBAlpha, 0),
        image(8, 4 * (frames ? frames : 1), kBitmapRGBAlpha, 0),
        background(24, 20, kBitmapRGBAlpha, 0);
    image.setFrameCount(frames ? frames : 1);
    background.setFrameCount(3);
    auto owned = std::make_unique<Bitmap>(24, 20, kBitmapRGBAlpha, 0);
    owned->setFrameCount(2);
    Renderer g(canvas);
    g.images[0] = &image;
    g.images[1] = &background;
    g.images[2] = owned.get();
    ColorBitmapRenderer clear(canvas);
    clear.fillRect(Rect(0, 0, 24, 20), Colors::kBlack);
    for (auto *b : {&image, &background, owned.get()}) {
      ColorBitmapRenderer fill(*b);
      fill.fillRect(b->getSize(), Colors::kWhite);
    }
    Rect clips[] = {Rect(0, 0, 24, 20), Rect(10, 8, 14, 12),
                    Rect(20, 16, 24, 20), Rect(14, 8, 18, 12)};
    // Provider clip is intentionally separate from original overlap call
    // checks.
    g.setClip(clips[clip]);
    DrawEvent event(g, clips[clip]);
    Style style;
    style.setBackColor(Color::fromInt(0xff102030u));
    style.setForeColor(Color::fromInt(0xff405060u));
    View view(Rect(3, 4, 27, 24));
    view.setStyle(new Style(style));
    Presonus::BackgroundPainter painter;
    Painter first(g, 0), second(g, 1);
    if (base) {
      painter.paint(Rect(3, 4, 27, 24), event, style);
    } else {
      Presonus::EQControl eq(presonus::dsp::EQControlBiquadPortTag{});
      struct Boundary : presonus::dsp::EQControlDrawBoundary {
        void releaseBuffer() override {}
        void initBands(Presonus::EQControl &) override {}
      } boundary;
      eq.bindPortableDrawBoundary(boundary);
      eq.bindPortableView(view);
      eq.setBufferedDraw(mode != 0);
      eq.bindPortablePrimaryParameter(primary < 0 ? nullptr : &p);
      eq.bindPortableHandleStyle(6, Color::fromInt(0xff708090u));
      eq.portableBandState().resize(1);
      auto &band = eq.portableBandState()[0];
      band.enabled = enabled;
      band.on = true;
      band.x = 12;
      band.y = 10;
      eq.portableParameterState().resize(1);
      eq.portableParameterState()[0].slot5 = selected < 0 ? nullptr : &sel;
      eq.portableParameterState()[0].slot4 = &active;
      eq.bindPortableImages(frames && !custom ? &image : nullptr,
                            bg ? &background : nullptr);
      if (frames && custom)
        eq.bindPortableBandImages({&image});
      eq.portablePixelCurve().assign(24, 10);
      eq.portableAmplitudeCurve().assign(24, 0.f);
      LinearInterpolator gain(-1, 1), y(0, 20), x(0, 24);
      eq.bindPortableInterpolators(gain, x, gain, y);
      if (mode != 3)
        eq.bindPortableOwnedBitmap(std::move(owned));
      eq.setPortableBufferState(mode != 3, mode == 1);
      if (painters == 1)
        eq.addBackgroundPainter(painter);
      if (painters == 2) {
        eq.addBackgroundPainter(first);
        eq.addBackgroundPainter(second);
      }
      eq.draw(event);
      if (mode == 1 && eq.portableBitmap()) {
        // Real ColorBitmapRenderer clears RGBA storage; original drawCurve was
        // sent to the external event, so the owned buffer remains black.
        const auto &data = eq.portableBitmap()->accessForRead();
        for (int y0 = 0; y0 < 20; ++y0)
          for (int x0 = 0; x0 < 24; ++x0) {
            const auto pixel = data.rgbaAt(x0, y0);
            assert(pixel.red == 0 && pixel.green == 0 && pixel.blue == 0 &&
                   pixel.alpha == 255);
          }
      }
      std::cout << "{\"dirty\":" << int(eq.portableBufferValid())
                << ",\"trace\":";
    }
    if (base)
      std::cout << "{\"dirty\":" << int(mode == 1) << ",\"trace\":";
    std::cout << '[';
    for (unsigned i = 0; i < g.trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << '[';
      for (unsigned j = 0; j < g.trace[i].size(); ++j) {
        if (j)
          std::cout << ',';
        std::cout << g.trace[i][j];
      }
      std::cout << ']';
    }
    std::cout << "]}\n";
  }
}
