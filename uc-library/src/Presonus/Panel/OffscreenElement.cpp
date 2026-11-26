#include "presonus/panel/OffscreenElement.hpp"

namespace Presonus::Panel {
OffscreenElement::OffscreenElement(int x, int y) : Element(x, y) {}
OffscreenElement::OffscreenElement(const ElementInfo &info) : Element(info) {}
void OffscreenElement::draw(IDisplay &display) {
  const Point origin{0, 0};
  if (needsToDraw()) {
    render(display, elementState().activation != 0);
    cachedBits_.resize(static_cast<std::size_t>(display.getScreenWidth()) *
                       ((display.getScreenHeight() + 7) / 8));
    display.getScreenBits(cachedBits_.data(), origin, drawingBounds());
    setDirty(0);
  } else {
    const auto &bounds = drawingBounds();
    const Point position{bounds.x, bounds.y};
    const Rectangle source{0, 0, bounds.width, bounds.height};
    display.copyBits(cachedBits_.data(), position, source);
  }
}
OffscreenElement::~OffscreenElement() = default;
void OffscreenElement::operator delete(void *receiver) noexcept {
  ::operator delete(receiver);
}
} // namespace Presonus::Panel
