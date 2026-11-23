#include "presonus/panel/StaticElement.hpp"

namespace Presonus::Panel {
StaticElement::StaticElement(int x, int y, const char *text)
    : OffscreenElement(x, y), text_(text) {}

StaticElement::~StaticElement() = default;

void StaticElement::setNeedsToDraw(bool) {}
} // namespace Presonus::Panel
