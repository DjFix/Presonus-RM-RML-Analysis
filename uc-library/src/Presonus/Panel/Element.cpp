#include "presonus/panel/Element.hpp"

namespace Presonus::Panel {
Element::Element(int x, int y) : elementState_{x, y, 1, 0} {}

void Element::activate(int mode) {
  if (elementState_.activation != mode) {
    elementState_.dirty = 1;
    elementState_.activation = mode;
  }
}

void Element::setNeedsToDraw(bool dirty) { setDirty(dirty); }

bool Element::needsToDraw() const { return elementState_.dirty != 0; }

Element::~Element() = default;

void Element::render(IDisplay &, bool) {}

unsigned int Element::deltaEncoder(int) { return 0; }
unsigned int Element::tap() { return 0; }
unsigned int Element::next() { return 0; }
unsigned int Element::getParam() { return 0; }
unsigned int Element::previous() { return 0; }
} // namespace Presonus::Panel
