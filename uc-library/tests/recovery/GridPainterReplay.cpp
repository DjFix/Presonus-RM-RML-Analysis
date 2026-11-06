#include "core/portable/gui/corefont.h"
#include "core/public/corememstream.h"
#include "presonus/GridPainter.hpp"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
using namespace Core;
using namespace Core::Portable;
using Trace = std::vector<std::vector<long long>>;
namespace {
std::vector<unsigned char> fontBytes;
std::unique_ptr<BitmapFont> font;
void loadFont() {
  std::ifstream file("third_party/ccl-framework/core/extras/fonts/tuffy16.fnt",
                     std::ios::binary);
  fontBytes.assign(std::istreambuf_iterator<char>(file), {});
  std::ifstream image("third_party/ccl-framework/core/extras/fonts/tuffy16.png",
                      std::ios::binary);
  std::vector<unsigned char> png{std::istreambuf_iterator<char>(image), {}};
  IO::MemoryStream stream(png.data(), png.size());
  auto *bitmap = Bitmap::loadPNGImage(stream);
  assert(bitmap);
  font = std::make_unique<BitmapFont>("grid-test", bitmap, true);
  assert(font->loadInplace(fontBytes.data(), fontBytes.size()));
}
void output(const Trace &t) {
  std::cout << '[';
  bool a = false;
  for (const auto &row : t) {
    if (a)
      std::cout << ',';
    a = true;
    std::cout << '[';
    bool b = false;
    for (auto v : row) {
      if (b)
        std::cout << ',';
      b = true;
      std::cout << v;
    }
    std::cout << ']';
  }
  std::cout << "]\n";
}
struct Renderer : ColorBitmapRenderer {
  Trace trace;
  bool hasFont = false;
  bool inText = false;
  explicit Renderer(Bitmap &b) : ColorBitmapRenderer(b) {}
  const BitmapFont *getFont(CStringPtr) const override {
    return hasFont ? font.get() : nullptr;
  }
  bool drawLine(PointRef a, PointRef b, ColorRef c) override {
    trace.push_back({1, a.x, a.y, b.x, b.y, uint32(c)});
    return ColorBitmapRenderer::drawLine(a, b, c);
  }
  bool fillRect(RectRef r, ColorRef c) override {
    trace.push_back({2, r.left, r.top, r.right, r.bottom, uint32(c)});
    return ColorBitmapRenderer::fillRect(r, c);
  }
  bool drawString(RectRef r, CStringPtr s, ColorRef c, CStringPtr name,
                  int align) override {
    std::vector<long long> row{3,        r.left,    r.top, r.right,
                               r.bottom, uint32(c), align};
    for (auto p = s; *p; ++p)
      row.push_back(static_cast<unsigned char>(*p));
    trace.push_back(row);
    // Real pinned CCL font texture and rendering provider.
    inText = true;
    bool result = ColorBitmapRenderer::drawString(r, s, c, name, align);
    inText = false;
    return result;
  }
  bool drawBitmap(PointRef p, Bitmap &b, RectRef r,
                  const BitmapMode *m = nullptr) override {
    if (!inText)
      trace.push_back({4, p.x, p.y, r.left, r.top, r.right, r.bottom});
    return ColorBitmapRenderer::drawBitmap(p, b, r, m);
  }
};
struct Provider : Presonus::IBackgroundGridProvider {
  Presonus::EQControl eq{presonus::dsp::EQControlBiquadPortTag{}};
  LinearInterpolator norm{0.f, 48.f}, x{-12.f, 76.f}, gain{0.f, 48.f},
      y{-12.f, 60.f};
  Provider() { eq.bindPortableInterpolators(norm, x, gain, y); }
  int toXGridPixel(float v) const override { return eq.toXGridPixel(v); }
  int toYGridPixel(float v) const override { return eq.toYGridPixel(v); }
};
const float values[] = {-12.f, 0.f,  6.f,  12.f, 24.f,
                        32.f,  36.f, 42.f, 48.f, 60.f};
Rect clips[] = {Rect(0, 0, 64, 48), Rect(8, 7, 54, 41), Rect(70, 60, 80, 70),
                Rect(30, 20, 20, 10)};
Color backs[] = {Color(12, 110, 240, 255), Color(250, 205, 0, 79)};
std::uint32_t pixelHash(const Bitmap &b) {
  std::uint32_t h = 2166136261u;
  const auto &data = b.accessForRead();
  for (int y = 0; y < data.height; ++y)
    for (int x = 0; x < data.width; ++x) {
      auto c = data.rgbaAt(x, y);
      for (auto v : {c.red, c.green, c.blue, c.alpha}) {
        h ^= v;
        h *= 16777619u;
      }
    }
  return h;
}
Color decodeColor(std::uint32_t c) {
  return Color(c & 255, (c >> 8) & 255, (c >> 16) & 255, (c >> 24) & 255);
}
void rasterOracle() {
  int ci, n;
  while (std::cin >> ci >> n) {
    Bitmap canvas(96, 80, kBitmapRGBAlpha);
    Renderer external(canvas);
    external.hasFont = true;
    DrawEvent event(external, clips[ci]);
    std::unique_ptr<Bitmap> cache;
    std::unique_ptr<Renderer> cached;
    Renderer *g = &external;
    for (int i = 0; i < n; ++i) {
      int len;
      std::cin >> len;
      std::vector<long long> row(len);
      for (auto &v : row)
        std::cin >> v;
      int op = row[0];
      if (op == 5) {
        cache = std::make_unique<Bitmap>(row[1], row[2], kBitmapRGBAlpha);
        cache->setAlphaChannelUsed(false);
        cached = std::make_unique<Renderer>(*cache);
        // Native fills before constructing the local DrawEvent; both origins
        // are zero and the renderer initially clips to the full bitmap.
        g = cached.get();
      } else if (op == 6) {
        assert(cache);
        external.drawBitmap(Point(row[1], row[2]), *cache,
                            Rect(row[3], row[4], row[5], row[6]));
        g = &external;
      } else if (op == 1)
        g->drawLine(Point(row[1], row[2]), Point(row[3], row[4]),
                    decodeColor(uint32(row[5])));
      else if (op == 2)
        g->fillRect(Rect(row[1], row[2], row[3], row[4]),
                    decodeColor(uint32(row[5])));
      else if (op == 3) {
        std::string text;
        for (unsigned k = 7; k < row.size(); ++k)
          text.push_back(char(row[k]));
        g->drawString(Rect(row[1], row[2], row[3], row[4]), text.c_str(),
                      decodeColor(uint32(row[5])), "grid-test", row[6]);
      } else
        assert(false);
    }
    std::cout << pixelHash(canvas) << '\n';
  }
}
void vectorChecks() {
  Provider provider;
  Presonus::GridPainter painter(provider);
  assert(painter.portableValues(static_cast<Presonus::GridPainter::Axis>(0))
             .count() == 0);
  assert(painter.portableValues(static_cast<Presonus::GridPainter::Axis>(1))
             .count() == 0);
  assert(painter.portableBitmap() == nullptr &&
         painter.portableRectangle() == Rect());
  auto axis = [](int a) { return static_cast<Presonus::GridPainter::Axis>(a); };
  for (int a : {0, 1, -1, 2147483647}) {
    painter.setGridValues(axis(a), values, 10);
    const auto &v = painter.portableValues(axis(a));
    assert(v.count() == 10);
    for (int i = 0; i < 10; ++i)
      assert(v[i] == values[i]);
    painter.setGridValues(axis(a), nullptr, -7);
    assert(v.count() == 0);
    painter.setGridValues(axis(a), values, 2);
    assert(v.count() == 2);
    painter.setGridValues(axis(a), nullptr, 0);
    assert(v.count() == 0);
  }
  presonus::grid_port::AxisState a, b;
  Presonus::GridPainter borrowed(a, b);
  borrowed.setGridOrientation(
      axis(0), static_cast<Presonus::GridPainter::LabelOrientation>(2), "int");
  borrowed.setGridOrientation(
      axis(-1), static_cast<Presonus::GridPainter::LabelOrientation>(4),
      "absent");
  assert(a.orientation == 2 && a.formatter == FormatterRegistry::find("int"));
  assert(b.orientation == 4 && b.formatter == nullptr);
}
} // namespace
int main(int argc, char **argv) {
  loadFont();
  FormatterRegistry::add(const_cast<Formatter *>(&IntFormatter::instance()));
  Provider provider;
  if (argc > 1 && std::string(argv[1]) == "--providers") {
    Trace result{{font->getLineHeight()}};
    for (float v : values) {
      CString32 t;
      t.appendFormat("%d", int(v));
      result.push_back({int(v), provider.toXGridPixel(v),
                        provider.toYGridPixel(v),
                        font->getStringWidth(t, t.length())});
    }
    output(result);
    return 0;
  }
  if (argc > 1 && std::string(argv[1]) == "--raster") {
    rasterOracle();
    return 0;
  }
  // Prewarm the real font's color bitmap cache so lifetime measurements isolate
  // GridPainter ownership, excluding legitimate shared font allocations.
  {
    Bitmap warm(64, 48, kBitmapRGBAlpha);
    Renderer g(warm);
    g.hasFont = true;
    g.drawString(Rect(0, 0, 64, 48), "12", Color(4, 30, 70, 255), "grid-test",
                 1);
  }
  vectorChecks();
  int cached, labels, hasFont, ox, oy, fx, fy, ci, bi, ri, repeat;
  while (std::cin >> cached >> labels >> hasFont >> ox >> oy >> fx >> fy >>
         ci >> bi >> ri >> repeat) {
    Bitmap canvas(96, 80, kBitmapRGBAlpha);
    const auto memoryBefore = Bitmap::getTotalBitmapMemory();
    Renderer g(canvas);
    g.hasFont = hasFont;
    Style style;
    style.setBackColor(backs[bi]);
    style.setForeColor(Color(4, 30, 70, 255));
    style.setFontName("grid-test");
    {
      Presonus::GridPainter painter(provider);
      auto ax = [](int a) {
        return static_cast<Presonus::GridPainter::Axis>(a);
      };
      painter.setGridValues(ax(0), values, 10);
      painter.setGridValues(ax(1), values, 10);
      painter.setGridOrientation(
          ax(0), static_cast<Presonus::GridPainter::LabelOrientation>(ox),
          fx ? "int" : nullptr);
      painter.setGridOrientation(
          ax(1), static_cast<Presonus::GridPainter::LabelOrientation>(oy),
          fy ? "int" : nullptr);
      painter.setPortableDrawingOptions(cached, labels);
      Rect r = ri ? Rect(3, 4, 67, 52) : Rect(0, 0, 64, 48);
      DrawEvent e(g, clips[ci]);
      painter.paint(r, e, style);
      if (repeat) {
        // Reuse preserves cache despite changed values/style/orientations.
        painter.setGridValues(ax(0), nullptr, 0);
        painter.paint(r, e, style);
        if (repeat == 2)
          painter.paint(Rect(0, 0, 65, 49), e, style);
      }
      g.trace.push_back({9, pixelHash(canvas)});
      output(g.trace);
    }
    assert(Bitmap::getTotalBitmapMemory() == memoryBefore);
  }
}
