#pragma once
#include "presonus/uc/element.hpp"

namespace Presonus::UC {
// Portable source port: original ARM layout and ordinary return declarations
// remain unresolved. Field names describe observed attribute roles.
class TemplateElement : public Element {
public:
  explicit TemplateElement(const MetaElement &metadata);
  ~TemplateElement() override;
  bool load(const ElementAttributes &attributes) override;
  bool save(ElementAttributes &attributes) const override;

private:
  Core::CString64 inherit_{};
  Core::CString64 paramlist_{};
  Core::CString64 classname_{};
  Core::CString64 classfallback_{};
  Core::CString64 classdata_{};
  int flags_ = 0;
};
} // namespace Presonus::UC
