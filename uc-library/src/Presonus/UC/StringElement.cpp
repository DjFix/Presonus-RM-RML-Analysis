#include "presonus/uc/StringElement.hpp"
namespace Presonus::UC {
StringElement::StringElement(const MetaElement &metadata)
    : Element(metadata), text_(nullptr) {}
StringElement::~StringElement() = default;
bool StringElement::load(const ElementAttributes &attributes) {
  text_ = attributes.lookupName("text");
  return Element::load(attributes);
}
bool StringElement::save(ElementAttributes &attributes) const {
  attributes.storeName("text", text_.str());
  return Element::save(attributes);
}
} // namespace Presonus::UC
