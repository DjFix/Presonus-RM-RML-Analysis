#include "presonus/panel/FillElement.hpp"

namespace Presonus::Panel {
FillElement::FillElement(int x, int y, int width, int height, int value)
    : Element(x, y), rectangle_{x, y, width, height}, value_(value) {}

FillElement::FillElement(const ElementInfo &info)
    : Element(info),
      rectangle_{info.word(4), info.word(8), info.word(12), info.word(16)} {}

FillElement::~FillElement() = default;

void FillElement::render(IDisplay &display, bool) {
  setDirty(0);
  display.fillRect(rectangle_);
}
} // namespace Presonus::Panel
