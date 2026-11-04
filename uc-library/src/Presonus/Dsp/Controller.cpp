#include "presonus/dsp/ControllerProperties.hpp"
#include <bit>
#include <cstring>
namespace Presonus::Dsp {
Controller::Controller(int id, const ParamDescriptorList *list) {
  // Native stores at +0x04,+0x08,+0x0c,+0x10,+0x14,+0x18,+0x1c,
  // +0x1d,+0x20,+0x24 are modeled explicitly. The native table word
  // at +0 is represented by the compiler-owned vptr, never an ARM address.
  state_.word04 = 0;
  state_.word08 = 0xffffffffu;
  state_.descriptorList = list;
  state_.descriptors = list ? &list->sourceDescriptors() : nullptr;
  state_.word10 = 0;
  state_.word14 = 0;
  state_.constructorId = id;
  state_.processDirty = 0;
  state_.byte1d = 0;
  state_.word20 = 0;
  state_.processRateBits = 0;
  state_.lookupByTag = false;
}
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
Controller::~Controller() { setTarget(nullptr); }
void Controller::setHandler(Core::IPropertyHandler *handler) {
  state_.handler = handler;
}
void Controller::setTarget(Core::IPropertyHandler *target) {
  if (state_.target == target)
    return;
  if (state_.target && state_.byte1d)
    state_.target->release();
  state_.target = target;
}
void Controller::makeTargetOwner() { state_.byte1d = 1; }
void Controller::release() { delete this; }
void Controller::sendProperty(Core::Property &property) {
  if (state_.target)
    state_.target->setProperty(property);
}
void Controller::sendProperty(ChannelProperty &property, bool channel) {
  if (channel)
    property.channel = std::bit_cast<int>(state_.word04);
  if (state_.target)
    state_.target->setProperty(property);
}
void Controller::setProperty(const Core::Property &property) {
  auto word = [&](unsigned offset) {
    std::uint32_t value;
    std::memcpy(&value,
                reinterpret_cast<const unsigned char *>(&property) + offset, 4);
    return value;
  };
  if (property.type == 1399157877)
    setupProcess(static_cast<const SetupProperty &>(property));
  else if (property.type == 1415672423) {
    state_.word04 = word(8);
    state_.processDirty = 1;
    state_.byte1d = word(12) & 1;
  } else if (property.type == 1348563553)
    setValue(std::bit_cast<int>(word(12)), std::bit_cast<float>(word(16)));
}
int Controller::canFloatPrecision(int precision) const {
  if (precision == 1)
    return (static_cast<unsigned>(state_.constructorId) >> 2) & 1;
  return precision == 0;
}
int Controller::canConfiguration(int inputs, int outputs) const {
  if (inputs == 1 && outputs == 1)
    return state_.constructorId & 1;
  if (inputs == 2 && outputs == 2)
    return (static_cast<unsigned>(state_.constructorId) >> 1) & 1;
  return 0;
}
int Controller::canSetup(const SetupProperty &property) const {
  return canConfiguration(property.inputs, property.outputs) &&
         canFloatPrecision(property.precision);
}
int Controller::usedInProcessContext() const {
  return ((static_cast<unsigned>(state_.constructorId) >> 3) ^ 1) & 1;
}
int Controller::getNumParameters() const {
  return state_.descriptorList ? state_.descriptorList->sourceCount() : 0;
}
void Controller::setDefaultValues() {
  if (!state_.descriptors)
    return;
  for (int i = 0; i < state_.descriptors->count(); ++i) {
    auto *p = state_.descriptors->at(i);
    if (!p)
      p = ParamDescriptorList::getError();
    setValue(p->sourceState().tag,
             std::bit_cast<float>(p->sourceState().word14));
  }
}
unsigned Controller::flushParameterChanges() {
  if (state_.processDirty && state_.target &&
      std::bit_cast<float>(state_.processRateBits) > 0.f) {
    state_.processDirty = 0;
    state_.word20 |= 1;
    doUpdates();
  }
  auto result = state_.word20;
  state_.word20 = 0;
  return result;
}
// Existing base native default doUpdates is bound separately before sealing.
} // namespace Presonus::Dsp
