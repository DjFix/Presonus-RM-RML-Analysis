#pragma once
#include "core/public/corememstream.h"
#include "presonus/uc/element.hpp"
namespace presonus::uc {
struct DataElementAccess;
}
namespace Presonus::UC {
// Portable source contract; native ARM layout and load/save return declarations
// are unresolved. Uses the current Element bool override contract.
class DataElement : public Element {
public:
  explicit DataElement(const MetaElement &metadata);
  ~DataElement() override;
  bool load(const ElementAttributes &attributes) override;
  bool save(ElementAttributes &attributes) const override;

private:
  friend struct presonus::uc::DataElementAccess;
  Core::CString32 type_;
  Core::IO::MemoryStream data_;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Independent portable access; does not assert original API declarations.
struct DataElementAccess {
  static const char *type(const Presonus::UC::DataElement &e) {
    return e.type_.str();
  }
  static Core::IO::MemoryStream &stream(Presonus::UC::DataElement &e) {
    return e.data_;
  }
};
} // namespace presonus::uc
