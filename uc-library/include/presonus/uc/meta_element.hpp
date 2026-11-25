#pragma once

#include "core/public/coretypes.h"

namespace Presonus::UC {

class Element;

class MetaElement {
public:
  using Factory = Element *(*)(const MetaElement &);

  // Portable initialization of the two observed metadata roles.
  MetaElement(Core::CStringPtr className, Factory factory)
      : className_(className), factory_(factory) {}

  bool isClass(const char *className) const;

private:
  Core::CStringPtr className_;
  [[maybe_unused]] Factory factory_;
};

} // namespace Presonus::UC
