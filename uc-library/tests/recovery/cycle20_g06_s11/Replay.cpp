#include "presonus/panel/FieldElement.hpp"

#include <iostream>

using Presonus::Panel::Element;
using Presonus::Panel::FieldElement;

[[gnu::noinline]] bool needsToDraw(const Element &element) {
  return element.needsToDraw();
}

int main() {
  Element element;
  FieldElement field("", nullptr);
  bool useField;
  unsigned int dirty;
  while (std::cin >> useField >> dirty) {
    auto &view = useField ? static_cast<Element &>(field) : element;
    view.setDirty(dirty);
    const bool observed =
        useField ? field.needsToDraw() : element.needsToDraw();
    if (observed != needsToDraw(view))
      return 3;
    std::cout << observed << '\n';
  }
}
