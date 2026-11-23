#include "core/portable/gui/coregraphics.h"
#include "presonus/ColorButton.hpp"
#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace Core;
using namespace Core::Portable;

namespace {
constexpr unsigned styleColor = 0xff223344;
constexpr unsigned channelColor = 0xff4973a0;
constexpr unsigned focusColor = 0xff010203;
const Rect bounds(0, 0, 22, 14);

struct Channel final : Presonus::SLChannelBase {
  explicit Channel(ColorParam &color) : color_(color) {}
  Parameter *getColorParameter() const override { return &color_; }
  ColorParam &color_;
};

struct Renderer final : ColorBitmapRenderer {
  explicit Renderer(Bitmap &bitmap) : ColorBitmapRenderer(bitmap) {}
  std::vector<std::string> events;

  bool fillRect(RectRef rect, ColorRef color) override {
    std::ostringstream event;
    event << "fill " << rect.left << ' ' << rect.top << ' ' << rect.right << ' '
          << rect.bottom << ' ' << static_cast<unsigned>(color);
    events.push_back(event.str());
    return ColorBitmapRenderer::fillRect(rect, color);
  }
  bool drawBitmap(PointRef point, Bitmap &bitmap, RectRef rect,
                  const BitmapMode *mode) override {
    if (mode)
      std::abort();
    std::ostringstream event;
    event << "bitmap " << point.x << ' ' << point.y << ' ' << rect.left << ' '
          << rect.top << ' ' << rect.right << ' ' << rect.bottom;
    events.push_back(event.str());
    return ColorBitmapRenderer::drawBitmap(point, bitmap, rect, mode);
  }
};

struct FocusProbe final : Control {
  using Control::drawFocusFrame;
};

struct TestColorButton final : ColorButton {
  using ColorButton::ColorButton;
  using ColorButton::isFocused;
};

void output(const Renderer &renderer) {
  for (const auto &event : renderer.events)
    std::cout << event << '\n';
}
} // namespace

int main() {
  ThemePainter::instance().setFocusColor(Color::fromInt(focusColor));
  ThemePainter::instance().setFocusBorder(Skin::kBorderLeftEdge);
  ThemePainter::instance().setFocusBorderWeight(2);
  std::string label;
  bool mixer, selection, casted, focused;
  int index, frames;
  while (std::cin >> label >> mixer >> selection >> casted >> index >>
         focused >> frames) {
    ParamInfo colorInfo{};
    colorInfo.type = ParamInfo::kColor;
    colorInfo.name[0] = 'c';
    ColorParam colorParameter(colorInfo);
    colorParameter.setColor(channelColor, false);
    ParamInfo indexInfo{};
    indexInfo.type = ParamInfo::kInt;
    indexInfo.name[0] = 'i';
    indexInfo.minValue = -40;
    indexInfo.maxValue = 40;
    NumericParam colorIndex(indexInfo);
    colorIndex.setValueFast(static_cast<float>(index));
    Channel channel(colorParameter);
    channel.bindColorIndexParameter(&colorIndex);
    Component groups;
    if (selection && !casted) {
      auto *line = new Component("line");
      line->addChild(new Component("not a channel"));
      groups.addChild(line);
    }
    Presonus::MixerClientComponentBase selected(
        groups, selection && casted ? &channel : nullptr);
    Bitmap canvas(22, 14), strip(9, 14);
    if (frames)
      strip.setFrameCount(frames);
    Renderer renderer(canvas);
    DrawEvent event(renderer, bounds);
    TestColorButton button(bounds, nullptr, &colorParameter);
    auto *style = new Style;
    style->setBackColor(Color::fromInt(styleColor));
    button.setStyle(style);
    button.isFocused(focused);
    button.bindDrawingSources(mixer ? &selected : nullptr,
                              frames ? &strip : nullptr);
    button.draw(event);
    std::cout << "case " << label << '\n';
    output(renderer);
    button.setStyle(nullptr);

    renderer.events.clear();
    FocusProbe reference;
    reference.setSize(bounds);
    reference.drawFocusFrame(event);
    std::cout << "focus-provider\n";
    output(renderer);
    std::cout << "end\n";
  }
}
