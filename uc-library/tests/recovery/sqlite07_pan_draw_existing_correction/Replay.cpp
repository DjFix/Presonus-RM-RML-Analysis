#include "core/portable/gui/coregraphics.h"
#include "presonus/PanControl.hpp"
#include <iostream>

using namespace Core;
using namespace Core::Portable;

struct RecordingRenderer : ColorBitmapRenderer {
  using ColorBitmapRenderer::ColorBitmapRenderer;
  int calls = 0;

  bool fillRect(RectRef rectangle, ColorRef color) override {
    ++calls;
    return ColorBitmapRenderer::fillRect(rectangle, color);
  }
  bool drawLine(PointRef start, PointRef end, ColorRef color) override {
    ++calls;
    return ColorBitmapRenderer::drawLine(start, end, color);
  }
};

int main() {
  for (bool vertical : {false, true}) {
    for (bool disabled : {false, true}) {
      for (bool enabled : {false, true}) {
        ParamInfo info{};
        info.type = ParamInfo::kFloat;
        info.minValue = 0.f;
        info.maxValue = 1.f;
        NumericParam parameter(info);
        parameter.setValueFast(.75f);
        parameter.enable(enabled);
        Presonus::PanControl control(Rect(7, 9, 112, 30), &parameter);
        control.isVertical(vertical);
        control.enable(!disabled);
        control.setStyle(new Style);
        Bitmap bitmap(140, 60);
        RecordingRenderer graphics(bitmap);
        DrawEvent event(graphics, Rect(1, 2, 54, 13));
        static_cast<View &>(control).draw(event);
        std::cout << vertical << ' ' << disabled << ' ' << enabled << ' '
                  << graphics.calls << '\n';
      }
    }
  }
}
