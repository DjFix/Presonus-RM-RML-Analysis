#include "presonus/uc/ComponentElement.hpp"

namespace Presonus::UC {
ComponentElement::ComponentElement(const MetaElement &metadata)
    : TemplateElement(metadata) {}
ComponentElement::~ComponentElement() = default;
bool ComponentElement::load(const ElementAttributes &attributes) {
  template_ = attributes.lookupName("template");
  name_ = attributes.lookupName("name");
  group_ = attributes.lookupName("group");
  return TemplateElement::load(attributes);
}
bool ComponentElement::save(ElementAttributes &attributes) const {
  attributes.storeName("template", template_.str());
  attributes.storeName("name", name_.str());
  attributes.storeName("group", group_.str());
  return TemplateElement::save(attributes);
}
} // namespace Presonus::UC
