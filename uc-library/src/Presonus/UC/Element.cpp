#include "presonus/uc/element.hpp"

#include <new>
#include <stdexcept>

namespace Presonus::UC {

Element::Element(const MetaElement &metadata) : metadata_(metadata) {}

Element::~Element() {
  for (auto *child : children_)
    delete child;
}

bool Element::isEmpty() const { return children_.isEmpty(); }

const MetaElement &Element::getMetaElement() const { return metadata_; }

int Element::getIndex(const Element *child) const {
  for (int index = 0; index < children_.count(); ++index)
    if (children_.at(index) == child)
      return index;
  return -1;
}

void Element::addChild(Element *child) {
  if (!child || child->parent_)
    throw std::invalid_argument("Element requires a detached child");
  for (auto *ancestor = this; ancestor; ancestor = ancestor->parent_)
    if (ancestor == child)
      throw std::invalid_argument("Element cannot adopt an ancestor");

  child->parent_ = this;
  try {
    if (!children_.add(child))
      throw std::bad_alloc();
  } catch (...) {
    child->parent_ = nullptr;
    throw;
  }
}

Element *Element::findChild(const char *name) const {
  for (auto *child : children_)
    if (child->name_ == name)
      return child;
  return nullptr;
}

} // namespace Presonus::UC
