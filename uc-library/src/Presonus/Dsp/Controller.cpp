#include "presonus/dsp/Controller.hpp"
namespace Presonus::Dsp {
const ParamDescriptor &Controller::descriptor(int tag) const {
  if (state_.descriptors) {
    if (state_.lookupByTag) {
      for (int i = 0; i < state_.descriptors->count(); ++i) {
        auto *candidate = state_.descriptors->at(i);
        // Native tag lookup requires nonnull entries; invalid native pointers
        // are outside this portable source-port contract.
        if (candidate && candidate->sourceState().tag == tag)
          return *candidate;
      }
    } else if (auto *candidate = state_.descriptors->at(tag)) {
      return *candidate;
    }
  }
  return *ParamDescriptorList::getError();
}
float Controller::getNormalized(int tag) const {
  return rangeToNormalizedValue(tag, getValue(tag));
}
float Controller::setNormalized(int tag, float value) {
  return setValue(tag, normalizedValueToRange(tag, value));
}
float Controller::normalizedValueToRange(int tag, float value) const {
  auto *curve = descriptor(tag).sourceState().interpolator;
  return curve ? curve->normalizedToRange(value) : value;
}
float Controller::rangeToNormalizedValue(int tag, float value) const {
  auto *curve = descriptor(tag).sourceState().interpolator;
  return curve ? curve->rangeToNormalized(value) : value;
}
float Controller::boundValue(int tag, float value) const {
  auto *curve = descriptor(tag).sourceState().interpolator;
  const float maximum = curve ? curve->getMaxRange() : 1.f;
  const float minimum = curve ? curve->getMinRange() : 0.f;
  if (value > maximum)
    return maximum;
  if (value < minimum)
    return minimum;
  return value;
}
} // namespace Presonus::Dsp
