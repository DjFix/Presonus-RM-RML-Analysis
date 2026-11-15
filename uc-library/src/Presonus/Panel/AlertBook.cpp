#include "presonus/panel/AlertBook.hpp"
namespace Presonus::Panel {
void AlertBook::setParamString(const char *text, int tag) {
  if (auto *p = parameters_.getParameterByTag(tag))
    if (auto *string = Core::Portable::StringParam::cast(p))
      string->fromString(text, false);
}
} // namespace Presonus::Panel
