#include "presonus/panel/OffscreenElement.hpp"

namespace Presonus::Panel {
OffscreenElement::OffscreenElement(int x, int y) : Element(x, y) {}
OffscreenElement::~OffscreenElement() = default;
void OffscreenElement::operator delete(void *receiver) noexcept {
  ::operator delete(receiver);
}
} // namespace Presonus::Panel
