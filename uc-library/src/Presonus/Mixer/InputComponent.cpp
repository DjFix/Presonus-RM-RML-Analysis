#include "presonus/mixer/InputComponent.hpp"
#include <cstring>
#include <stdexcept>
namespace {
std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
void changed(float &cached, float value, int tag,
             presonus::input_port::Property &property) {
  if (cached == value)
    return;
  cached = value;
  property.append(tag, bits(value));
}
Core::Portable::Component *aux(presonus::input_port::State &s, int index) {
  if (s.auxiliaries.empty())
    return nullptr;
  return index >= 0 && static_cast<std::size_t>(index) < s.auxiliaries.size()
             ? s.auxiliaries[index]
             : s.auxError;
}
} // namespace
namespace presonus::input_port {
void Property::append(int tag, std::uint32_t value) {
  if (count > 59)
    return;
  if (count < 0)
    throw std::out_of_range("negative property count");
  entries[count++] = {tag, value};
}
} // namespace presonus::input_port
namespace Presonus::Mixer {
void InputComponent::assignSubsUpdate(Dsp::MultiParamProperty &opaque) {
  auto &p = providers.resolveProperty(&opaque);
  for (std::size_t i = 0; i < state.subgroups.size(); ++i) {
    float value = i < 4 ? state.parametersByRole[5 + i]->getValue() : 0.f;
    auto *group = state.subgroups[i];
    if (group && group->linked && group->linked->getValue() > 0.f) {
      if (group->slave)
        continue;
      auto even = i & 254u;
      changed(state.cachedLevels.at(even), value * state.levels[0],
              static_cast<int>(even) + 16, p);
      changed(state.cachedLevels.at(even + 1), value * state.levels[1],
              static_cast<int>(even) + 17, p);
    } else {
      changed(state.cachedLevels.at(i), value * state.levels[5],
              static_cast<int>(i) + 16, p);
    }
  }
}
bool InputComponent::isPostFaderAux(int index) {
  auto *a = aux(state, index);
  if (!a)
    throw std::invalid_argument("post-fader lookup requires aux provider");
  auto *p = providers.auxPrePost(*a);
  return p && p->getValue() == 2.f;
}
bool InputComponent::isSubgroupModeAux(int index) {
  auto *a = aux(state, index);
  if (!a)
    throw std::invalid_argument("subgroup lookup requires aux component");
  auto *p = a->getParameterByTag(411);
  return p && p->getValue() > 0.f;
}
void InputComponent::assignLRUpdate(Dsp::MultiParamProperty &opaque) {
  auto &p = providers.resolveProperty(&opaque);
  const bool lr = state.parametersByRole[2]->getNormalized() == 1.f;
  const bool center = state.parametersByRole[3]->getNormalized() == 1.f;
  changed(state.cachedLevels[4], lr ? state.levels[0] : 0.f, 20, p);
  changed(state.cachedLevels[5], lr ? state.levels[1] : 0.f, 21, p);
  changed(state.cachedLevels[6], center ? state.levels[2] : 0.f, 22, p);
}
bool InputComponent::isGlobalAuxMute() {
  if (!state.globalCache)
    throw std::invalid_argument("global mute cache required");
  auto &cache = *state.globalCache;
  if (!cache.component)
    cache.component = state.globalComponent;
  if (!cache.parameter) {
    if (!cache.component)
      throw std::invalid_argument("global component required");
    cache.parameter = cache.component->getParameterByTag(28);
  }
  return cache.parameter && cache.parameter->getValue() > 0.f;
}
void InputComponent::setSectionCoeffChanged(int section) {
  providers.channelSectionChanged(section);
  if (section == 0) {
    state.changed[5] = state.changed[1] = state.changed[2] = state.changed[3] =
        1;
    providers.meterLevel(state.channelIndex, state.levels[5]);
  } else if (section == 1)
    state.changed[4] = 1;
}
void InputComponent::solo(presonus::input_port::Property &p) {
  changed(state.cachedLevels[11], state.levels[3], 27, p);
  changed(state.cachedLevels[12], state.levels[4], 28, p);
}
void InputComponent::soloUpdate(Dsp::MultiParamProperty &opaque) {
  solo(providers.resolveProperty(&opaque));
}
void InputComponent::linkUpdate(Dsp::MultiParamIntProperty &opaque) {
  auto *parameter = state.parametersByRole[0];
  if (!parameter)
    return;
  const int value = static_cast<int>(parameter->getValue());
  if (state.cachedIntegers[3] == value)
    return;
  state.cachedIntegers[3] = value;
  providers.resolveProperty(&opaque).append(5,
                                            static_cast<std::uint32_t>(value));
}
void InputComponent::doUpdates() {
  providers.channelUpdates();
  const int channel = state.channelType == 7 || state.channelType == 1
                          ? 0
                          : state.channelIndex & 1;
  presonus::input_port::Property floating, integer;
  floating.id = 1836085869u;
  integer.id = 1836085871u;
  floating.channel = integer.channel = channel;
  const int flagIndices[] = {1, 2, 3, 5};
  const int slots[] = {0x5c, 0x64, 0x68, 0x58};
  for (int i = 0; i < 4; ++i)
    if (state.changed[flagIndices[i]])
      providers.update(slots[i], floating);
  if (state.changed[4])
    solo(floating);
  if (state.changed[0])
    providers.update(0x6c, integer);
  const int roles[] = {1, 9, 4};
  const int cacheIndices[] = {0, 2, 1};
  const int tags[] = {0, 4, 1};
  for (int i = 0; i < 3; ++i) {
    auto *parameter = state.parametersByRole[roles[i]];
    if (!parameter)
      continue;
    float f = parameter->getValue();
    int value = i == 1 ? f == 0.f : static_cast<int>(f);
    auto &cache = state.cachedIntegers[cacheIndices[i]];
    if (cache != value) {
      cache = value;
      integer.append(tags[i], static_cast<std::uint32_t>(value));
    }
  }
  if (floating.count > 0)
    providers.submit(floating);
  if (integer.count > 0)
    providers.submit(integer);
}
bool InputComponent::auxAssigned(int index) {
  if (!state.parameters)
    throw std::invalid_argument("parameter component required");
  const auto tag = static_cast<int>(static_cast<std::uint32_t>(index) + 256u);
  auto *p = state.parameters->getParameterByTag(tag);
  return !p || p->getValue() > 0.f;
}
} // namespace Presonus::Mixer
