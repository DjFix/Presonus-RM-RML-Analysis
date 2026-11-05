#include "core/portable/gui/coregraphics.h"
#include "presonus/PanControl.hpp"
#include <iostream>
#include <string>
#include <vector>
using namespace Core;
using namespace Core::Portable;
struct Renderer : ColorBitmapRenderer {
  std::vector<std::string> calls;
  Renderer(Bitmap &b) : ColorBitmapRenderer(b) {}
  static std::string point(PointRef p) {
    return std::to_string(p.x) + ":" + std::to_string(p.y);
  }
  static std::string rect(RectRef r) {
    return std::to_string(r.left) + ":" + std::to_string(r.top) + ":" +
           std::to_string(r.right) + ":" + std::to_string(r.bottom);
  }
  bool fillRect(RectRef r, ColorRef c) override {
    calls.push_back("fill:" + rect(r) + ":" + std::to_string(c));
    return ColorBitmapRenderer::fillRect(r, c);
  }
  bool drawLine(PointRef a, PointRef b, ColorRef c) override {
    calls.push_back("line:" + point(a) + ":" + point(b) + ":" +
                    std::to_string(c));
    return ColorBitmapRenderer::drawLine(a, b, c);
  }
  bool drawBitmap(PointRef p, Bitmap &b, RectRef r,
                  const BitmapMode *m) override {
    calls.push_back("bitmap:" + point(p) + ":" + rect(r));
    return ColorBitmapRenderer::drawBitmap(p, b, r, m);
  }
};
int main() {
  int target, width, height, mark, stereo, link, side, aux, primary, image,
      enabled, bw, bh, frames;
  float value, other;
  while (std::cin >> target >> width >> height >> mark >> stereo >> link >>
         side >> aux >> primary >> image >> enabled >> bw >> bh >> frames >>
         value >> other) {
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    NumericParam p(info), sp(info), lp(info), rp(info), ap(info);
    p.setValueFast(value);
    sp.setValueFast(stereo);
    lp.setValueFast(link);
    rp.setValueFast(side);
    ap.setValueFast(other);
    p.enable(enabled);
    Presonus::PanControl pan(Rect(0, 0, width, height), primary ? &p : nullptr);
    DefaultAllocatedAttributes a;
    a.set("valueBarWidth", mark);
    pan.setAttributes(a);
    pan.setSize(Rect(0, 0, width, height));
    pan.bindPanParameters({&sp, &lp, nullptr, &rp, aux ? &ap : nullptr});
    Bitmap source(bw, bh);
    source.setFrameCount(frames);
    if (image)
      pan.setImage(BitmapReference(&source));
    auto *style = new Style;
    Color markColor;
    markColor(0x12345678);
    style->setTextColor(markColor);
    Color lineColor;
    lineColor(0x23456789);
    style->setBackColorDisabled(lineColor);
    pan.setStyle(style);
    Bitmap output(400, 100);
    Renderer renderer(output);
    DrawEvent e(renderer, Rect(0, 0, width, height));
    if (target == 1)
      pan.drawValueMark(e);
    else
      pan.drawImagePanner(e);
    std::cout << renderer.calls.size();
    for (auto &call : renderer.calls)
      std::cout << ' ' << call;
    std::cout << '\n';
    // BitmapReference is borrowed by the CCL view; detach before stack bitmap
    // dies.
    pan.setImage(BitmapReference());
    pan.setParameter(nullptr);
    pan.setStyle(nullptr);
  }
}
