#include "presonus/uc/DataElement.hpp"
namespace Presonus::UC {
DataElement::DataElement(const MetaElement &metadata) : Element(metadata) {}
DataElement::~DataElement() = default;
bool DataElement::load(const ElementAttributes &attributes) {
  type_ = attributes.lookupName("type");
  return Element::load(attributes);
}
bool DataElement::save(ElementAttributes &attributes) const {
  attributes.storeName("type", type_.str());
  return Element::save(attributes);
}
} // namespace Presonus::UC
