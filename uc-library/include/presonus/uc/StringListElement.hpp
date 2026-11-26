#pragma once
#include "presonus/uc/element.hpp"
namespace Presonus::UC {
class StringListElement : public Element {
public:
  explicit StringListElement(const MetaElement &metadata);
  ~StringListElement() override;
  int countStrings() const;
  // Requires an in-range, nonnull StringElement child. Original invalid pointer
  // tokens are excluded from this typed portable source-port contract.
  const char *getString(int index) const;
};
} // namespace Presonus::UC
