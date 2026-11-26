#include "presonus/uc/TemplateElement.hpp"
#include "core/public/coreenumdef.h"

namespace Presonus::UC {
namespace {
// Original application table: public=1, mutable=2, private-params=4.
constexpr Core::EnumInfo flagsInfo[] = {
    {"public", 1}, {"mutable", 2}, {"private-params", 4}, {nullptr, 0}};
} // namespace
TemplateElement::TemplateElement(const MetaElement &metadata)
    : Element(metadata) {}
TemplateElement::~TemplateElement() = default;
bool TemplateElement::load(const ElementAttributes &attributes) {
  inherit_ = attributes.lookupName("inherit");
  paramlist_ = attributes.lookupName("paramlist");
  classname_ = attributes.lookupName("classname");
  classfallback_ = attributes.lookupName("classfallback");
  classdata_ = attributes.lookupName("classdata");
  const auto *flags = attributes.lookupName("flags");
  flags_ = Core::EnumInfo::parseMultiple(Core::ConstString(flags ? flags : ""),
                                         flagsInfo);
  return Element::load(attributes);
}
bool TemplateElement::save(ElementAttributes &attributes) const {
  attributes.storeName("inherit", inherit_.str());
  attributes.storeName("paramlist", paramlist_.str());
  attributes.storeName("classname", classname_.str());
  attributes.storeName("classfallback", classfallback_.str());
  attributes.storeName("classdata", classdata_.str());
  Core::CString128 flags;
  Core::EnumInfo::printMultiple(flags, flags_, flagsInfo);
  attributes.storeName("flags", flags.str());
  return Element::save(attributes);
}
} // namespace Presonus::UC
