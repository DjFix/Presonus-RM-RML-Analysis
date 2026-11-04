#include "presonus/mixer/MixerComponent.hpp"
#include "core/portable/corepersistence.h"
#include "core/system/coredebug.h"
#include <cstring>

namespace Presonus::Mixer {
void MixerComponent::paramChanged(Core::Portable::Parameter *parameter,
                                  int flags) {
  services_.serverParamChanged(*this, parameter, flags);
}
void MixerComponent::release() { delete this; }
ChannelComponent *MixerComponent::findChannelOwningParameter(
    const Core::Portable::Parameter &parameter) const {
  for (int i = 0; i < state_.channels.count(); ++i) {
    auto *channel = state_.channels.at(i);
    if (services_.parameterComponent(*channel).getParameterByTag(
            parameter.getTag()) == &parameter)
      return channel;
  }
  return nullptr;
}
void MixerComponent::restoreMutes(Core::Portable::Attributes &attributes,
                                  const MixerComponentBase::Filter &filter) {
  if (attributes.isEmpty())
    return;
  Core::Portable::InputStorage storage(
      attributes, services_.storageFilter(filter.selector, false));
  services_.load(storage);
}
void MixerComponent::doMute(ChannelComponent *channel) {
  if (!state_.muteEnabled || !state_.muteActive ||
      services_.muteExcluded(*channel))
    return;
  auto &destination = services_.muteDestination(*channel);
  const auto &source = services_.muteSource(*channel);
  destination.setValue(source.getValue() == 0.f ? 1.f : 0.f, true);
}
void MixerComponent::presetStored(
    const Presonus::Panel::PresetComponent &preset, int index) {
  Core::DebugPrintf("MixerComponent::presetStored: %d\n", index);
  const char *type = services_.presetType(preset);
  if (type && std::strcmp(type, "scene") == 0)
    services_.command("StoreAVBScene", "scene", index);
}
void MixerComponent::onCascadeChannelSelect(int, int) {
  const int count = state_.channels.count();
  for (int i = 0; i < count; ++i)
    services_.selection(*state_.channels.at(i)).setValue(0.f, false);
  state_.cascadeSelected = true;
  state_.cascadeDirty = true;
}
Presonus::LinkableComponent *
MixerComponent::getGeqLinkPartner(Presonus::LinkableComponent *target) {
  for (int i = 0; i < state_.equalizers.count(); ++i) {
    if (state_.equalizers.at(i) != target)
      continue;
    if ((i & 1) && state_.equalizers.at(i - 1))
      return state_.equalizers.at(i - 1);
    return i + 1 < state_.equalizers.count() ? state_.equalizers.at(i + 1)
                                             : nullptr;
  }
  return nullptr;
}
ChannelComponent *MixerComponent::getLinkPartner(
    Presonus::LinkableComponent *target,
    const Core::Vector<ChannelComponent *> &channels) {
  for (int i = 0; i < channels.count(); ++i) {
    if (services_.linkIdentity(channels.at(i)) != target)
      continue;
    if ((i & 1) && channels.at(i - 1))
      return channels.at(i - 1);
    return i + 1 < channels.count() ? channels.at(i + 1) : nullptr;
  }
  return nullptr;
}
void MixerComponent::rememberMutes(Core::Portable::Attributes &attributes,
                                   const MixerComponentBase::Filter &filter) {
  attributes.removeAll();
  Core::Portable::AttributesBuilder builder(attributes);
  Core::Portable::OutputStorage storage(
      builder, services_.storageFilter(filter.selector, false));
  services_.save(storage);
}
} // namespace Presonus::Mixer
