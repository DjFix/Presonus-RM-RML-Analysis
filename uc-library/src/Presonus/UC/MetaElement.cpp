#include "presonus/uc/meta_element.hpp"

#include <cstring>

namespace Presonus::UC {

bool MetaElement::isClass(const char *className) const {
  return std::strcmp(className_ ? className_ : "",
                     className ? className : "") == 0;
}

} // namespace Presonus::UC
