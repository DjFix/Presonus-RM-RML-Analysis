#include "presonus/panel/Element.hpp"

namespace Presonus::Panel {
unsigned int Element::deltaEncoder(int) { return 0; }
unsigned int Element::tap() { return 0; }
unsigned int Element::next() { return 0; }
unsigned int Element::getParam() { return 0; }
unsigned int Element::previous() { return 0; }
} // namespace Presonus::Panel
