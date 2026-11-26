#pragma once
#include "presonus/uc/element.hpp"
namespace Presonus::UC {
class StringElement : public Element {
public:
  explicit StringElement(const MetaElement &metadata);
  ~StringElement() override;
  bool load(const ElementAttributes &attributes) override;
  bool save(ElementAttributes &attributes) const override;
  // Independent typed source-port accessor; no recovered original identity.
  const char *text() const { return text_.str(); }

private:
  Core::CString128 text_;
};
} // namespace Presonus::UC
