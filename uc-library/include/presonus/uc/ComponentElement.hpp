#pragma once
#include "presonus/uc/TemplateElement.hpp"

namespace Presonus::UC {
// Portable source port: original ARM layout and ordinary return declarations
// remain unresolved. Field names describe observed attribute roles.
class ComponentElement : public TemplateElement {
public:
  explicit ComponentElement(const MetaElement &metadata);
  ~ComponentElement() override;
  bool load(const ElementAttributes &attributes) override;
  bool save(ElementAttributes &attributes) const override;

private:
  Core::CString64 template_{};
  Core::CString64 name_{};
  Core::CString64 group_{};
};
} // namespace Presonus::UC
