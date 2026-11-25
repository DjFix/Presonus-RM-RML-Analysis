#include "core/portable/gui/coregraphics.h"
#include "presonus/VUMeterControl.hpp"

#include <array>
#include <iostream>
#include <string>
#include <vector>

namespace {
using Core::PointRef;
using Core::RectRef;
using Core::Portable::Bitmap;
using Core::Portable::BitmapMode;

struct Renderer final : Core::Portable::ColorBitmapRenderer {
  Renderer(Bitmap &target, const Presonus::VUMeterControl &meter,
           const Bitmap &source)
      : ColorBitmapRenderer(target), meter(meter), source(source) {}

  bool drawBitmap(PointRef point, Bitmap &bitmap, RectRef rect,
                  const BitmapMode *mode) override {
    calls.push_back(
        {&bitmap == &source, point.x, point.y, rect.left, rect.top, rect.right,
         rect.bottom, meter.portableDirty(),
         ColorBitmapRenderer::drawBitmap(point, bitmap, rect, mode)});
    return calls.back()[8];
  }

  const Presonus::VUMeterControl &meter;
  const Bitmap &source;
  std::vector<std::array<int, 9>> calls;
};

void drawView(Core::Portable::View &view,
              const Core::Portable::DrawEvent &event) {
  view.draw(event);
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  bool dirty = std::stoi(argv[1]) != 0;
  bool hasBitmap = std::stoi(argv[2]) != 0;
  int frame = std::stoi(argv[3]);
  constexpr int frames = 4;
  Core::Rect area(0, 0, 16, 16);
  Bitmap source(12, 40), target(16, 16), referenceTarget(16, 16);
  source.setFrameCount(frames);
  Presonus::VUMeterControl meter(area), reference(area);
  for (auto *control : {&meter, &reference}) {
    control->portableBindBitmaps(hasBitmap ? &source : nullptr, nullptr,
                                 nullptr);
    control->portableBindFrameState(frame, frames, 0, dirty);
  }
  Renderer renderer(target, meter, source);
  Renderer referenceRenderer(referenceTarget, reference, source);
  const Core::Portable::DrawEvent event(renderer, area);
  const Core::Portable::DrawEvent referenceEvent(referenceRenderer, area);
  reference.PotControl::draw(referenceEvent);
  drawView(meter, event);
  const auto after = meter.portableState();
  std::cout << meter.portableDirty() << ' '
            << (renderer.calls == referenceRenderer.calls) << ' '
            << after.previousValue << ' ' << renderer.calls.size();
  for (const auto &call : renderer.calls)
    for (int value : call)
      std::cout << ' ' << value;
  std::cout << '\n';
}
