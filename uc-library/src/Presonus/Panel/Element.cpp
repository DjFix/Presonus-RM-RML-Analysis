#include "presonus/panel/Element.hpp"
#include "presonus/panel/FieldElement.hpp"

namespace Presonus::Panel {
Element::Element(const ElementInfo &info)
    : info_(info), elementState_{info.word(4), info.word(8), 1, 0} {}

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

void Element::draw(IDisplay &display) {
  render(display, elementState_.activation != 0);
}

bool Element::editable() {
  if (!info_.observation[92])
    return false;
  auto *field = dynamic_cast<FieldElement *>(this);
  auto *parameter = field ? field->getParam() : nullptr;
  return !parameter || parameter->isEnabled();
}

unsigned int Element::deltaEncoder(int) { return 0; }
unsigned int Element::tap() { return 0; }
unsigned int Element::next() { return 0; }
unsigned int Element::getParam() { return 0; }
unsigned int Element::previous() { return 0; }
} // namespace Presonus::Panel
