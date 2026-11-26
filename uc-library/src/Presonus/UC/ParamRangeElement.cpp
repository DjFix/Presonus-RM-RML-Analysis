#include "presonus/uc/ParamRangeElement.hpp"
namespace Presonus::UC {
ParamRangeElement::ParamRangeElement(const MetaElement &metadata)
    : Element(metadata) {}
ParamRangeElement::~ParamRangeElement() = default;
bool ParamRangeElement::load(const ElementAttributes &attributes) {
  Element::load(attributes);
  auto parse = [&](double &value, const char *key, unsigned bit) {
    if (parseValue(value, attributes.lookupName(key)))
      presence_ |= bit;
    else
      presence_ &= ~bit;
  };
  parse(range_.minimum, "min", 1);
  parse(range_.maximum, "max", 2);
  parse(range_.midpoint, "mid", 4);
  parse(range_.defaultValue, "def", 8);
  if (!(presence_ & 8))
    range_.defaultValue = range_.minimum;
  double steps = 0;
  parse(steps, "steps", 16);
  // Native __aeabi_d2iz comparison is bounded to finite int-representable
  // inputs.
  range_.steps = static_cast<int>(steps);
  range_.units = attributes.lookupName("units");
  range_.curve = attributes.lookupName("curve");
  return true;
}
bool ParamRangeElement::save(ElementAttributes &attributes) const {
  auto store = [&](const char *key, double value) {
    Core::CString32 text;
    text.appendFormat("%lf", value);
    attributes.storeName(key, text.str());
  };
  store("min", range_.minimum);
  store("max", range_.maximum);
  store("mid", range_.midpoint);
  store("def", range_.defaultValue);
  Core::CString32 steps;
  steps.appendFormat("%d", range_.steps);
  attributes.storeName("steps", steps.str());
  attributes.storeName("units", range_.units.str());
  attributes.storeName("curve", range_.curve.str());
  return Element::save(attributes);
}
} // namespace Presonus::UC
