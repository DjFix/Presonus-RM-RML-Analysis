#pragma once
#include "presonus/uc/element.hpp"
#include "presonus/uc/param_range.hpp"
namespace Presonus::UC {
// Portable storage; original ARM layout and ordinary return spelling
// unresolved.
class ParamRangeElement : public Element {
public:
  explicit ParamRangeElement(const MetaElement &metadata);
  ~ParamRangeElement() override;
  bool load(const ElementAttributes &attributes) override;
  bool save(ElementAttributes &attributes) const override;
  const ParamRange &range() const { return range_; }
  unsigned presence() const { return presence_; }

private:
  ParamRange range_;
  unsigned presence_ = 0;
};
} // namespace Presonus::UC
