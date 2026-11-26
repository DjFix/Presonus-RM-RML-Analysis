#include "presonus/uc/StringListElement.hpp"
#include "presonus/uc/StringElement.hpp"
#include <stdexcept>
namespace Presonus::UC {
StringListElement::StringListElement(const MetaElement &metadata)
    : Element(metadata) {}
StringListElement::~StringListElement() = default;
int StringListElement::countStrings() const {
  return presonus::uc::ElementAccess::childCount(*this);
}
const char *StringListElement::getString(int index) const {
  if (index < 0 || index >= countStrings())
    throw std::out_of_range("StringListElement requires an in-range child");
  return static_cast<const StringElement *>(
             presonus::uc::ElementAccess::childAt(*this, index))
      ->text();
}
} // namespace Presonus::UC
