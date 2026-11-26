#include "presonus/panel/StaticElement.hpp"

namespace Presonus::Panel {
StaticElement::StaticElement(int x, int y, const char *text)
    : OffscreenElement(x, y), text_(text) {}

StaticElement::StaticElement(const ElementInfo &info)
    : OffscreenElement(info), text_(info.name()) {}

void StaticElement::render(IDisplay &display, bool force) {
  setDirty(0);
  auto &bounds = drawingBounds();
  const auto &info = sourceInfo();
  if (bounds.width <= 0 || bounds.height <= 0) {
    int x = elementState().x;
    if (info.word(88) == 2) {
      int length = display.pixelLength(text_.c_str());
      if (info.word(12) > 0 && length >= info.word(12))
        length = info.word(12);
      x -= length;
    }
    display.moveTo(x, elementState().y);
    display.drawString(text_.c_str(), info.word(12), &bounds);
  }
  display.moveTo(bounds.x + 1, bounds.y + 1);
  const int color = info.word(84);
  display.setTextColor(color);
  if (color == 0 || color == 1) {
    if (color == 0)
      display.eraseRect(bounds);
    else
      display.fillRect(bounds);
    display.setTextColor(color);
    display.drawString(text_.c_str(), bounds.width, nullptr);
  }
  if (force)
    display.invertRect(bounds);
}

StaticElement::~StaticElement() = default;

void StaticElement::setNeedsToDraw(bool) {}
} // namespace Presonus::Panel
