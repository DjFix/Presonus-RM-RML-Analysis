#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"

#include <cstring>

namespace Presonus {
Core::Portable::Component *
MixerClientComponentBase::getChannelGroup(ChannelType type) const {
  const char *name;
  switch (static_cast<int>(type)) {
  case 0:
    name = "line";
    break;
  case 1:
    name = "return";
    break;
  case 2:
    name = "fxreturn";
    break;
  case 3:
    name = "talkback";
    break;
  case 4:
    name = "aux";
    break;
  case 5:
    name = "fxbus";
    break;
  case 6:
    name = "sub";
    break;
  case 7:
    name = "main";
    break;
  case 8:
    name = "mono";
    break;
  case 10:
    name = "signalgen";
    break;
  default:
    return nullptr;
  }
  return channelGroups_->findChild(name);
}

ChannelType MixerClientComponentBase::getChannelGroupType(
    const Core::Portable::Component &group) const {
  const char *names[] = {"line", "return",   "fxreturn", "talkback",
                         "aux",  "fxbus",    "sub",      "main",
                         "mono", "signalgen"};
  for (int i = 0; i < 10; ++i)
    if (std::strcmp(group.getName(), names[i]) == 0)
      return static_cast<ChannelType>(i == 9 ? 10 : i);
  return static_cast<ChannelType>(-1);
}

SLChannelBase *MixerClientComponentBase::getSelectedChannel() const {
  if (selectedChannel_)
    return selectedChannel_;
  for (int type = 0; type < 9; ++type) {
    auto *group = getChannelGroup(static_cast<ChannelType>(type));
    if (!group)
      continue;
    for (int index = 0; index < group->countChildren(); ++index) {
      auto *channel =
          Core::Portable::core_cast<SLChannelBase>(group->getChild(index));
      if (!channel)
        continue;
      auto *selection = channel->getSelectionParameter();
      if (selection && selection->getValue() > 0.f) {
        selectedChannel_ = channel;
        break;
      }
    }
  }
  return selectedChannel_;
}

namespace {
struct PresetLabel {
  const char *identifier;
  const char *typeName;
  const char *suggestion;
};
constexpr PresetLabel presetLabels[] = {
    {"scene", "Scene", "New Scene"},
    {"channel", "Channel", "New Channel"},
    {"geq", "GEQ", "New GEQ"},
    {"reverb", "Reverb", "New Reverb"},
    {"delay", "Delay", "New Delay"},
    {"mixscene", "Mix Scene", "mixscene"},
    {"mutegroup", "Mute Group", "mutegroup"},
};

const PresetLabel *findPresetLabel(IPresetHandler::PresetType type) {
  const auto index = static_cast<unsigned>(type);
  return index < sizeof(presetLabels) / sizeof(presetLabels[0])
             ? &presetLabels[index]
             : nullptr;
}
} // namespace

MixerClientComponentBase *MixerClientComponentBase::getMasterMixer() const {
  return state_.masterMixer;
}

MixerClientComponentBase *MixerClientComponentBase::getSlaveMixer() const {
  return state_.slaveMixer;
}

void MixerClientComponentBase::setMasterMixer(MixerClientComponentBase *mixer) {
  state_.masterMixer = mixer;
}

void MixerClientComponentBase::bindGeqs(
    const Core::ConstVector<Core::Portable::Component *> *geqs) {
  state_.geqs = geqs;
  state_.hasGeqConfiguration = geqs != nullptr;
  state_.geqCountWord = geqs ? static_cast<std::uint32_t>(geqs->count()) : 0U;
}

Core::Portable::Component *
MixerClientComponentBase::getMixGeq(int index) const {
  const auto *geqs = state_.geqs;
  if (!geqs)
    return nullptr;
  // The original ARM add wraps before the signed range test.
  const auto shifted = static_cast<std::uint32_t>(index) + 2U;
  std::int32_t slot;
  std::memcpy(&slot, &shifted, sizeof(slot));
  if (slot >= geqs->count())
    return nullptr;
  return slot >= 0 ? geqs->at(slot) : geqs->getError();
}

Core::Portable::Component *
MixerClientComponentBase::getMainGeq(bool last) const {
  const auto *geqs = state_.geqs;
  if (!geqs)
    return nullptr;
  if (!last)
    return geqs->isEmpty() ? geqs->getError() : geqs->at(0);
  const auto count = getNumGeqs();
  return count > 0 && count <= geqs->count() ? geqs->at(count - 1)
                                             : geqs->getError();
}

bool MixerClientComponentBase::isChannelComponent(
    Core::Portable::Component *component) const {
  if (!component || !Core::Portable::core_cast<SLChannelBase>(component))
    return false;
  const auto *parent = component->getParent();
  return parent && parent != channelGroups_ &&
         static_cast<int>(getChannelGroupType(*parent)) >= 0;
}

IPresetHandler::PresetType
MixerClientComponentBase::translatePresetType(const char *type) const {
  if (type) {
    for (unsigned index = 0;
         index < sizeof(presetLabels) / sizeof(presetLabels[0]); ++index)
      if (std::strcmp(type, presetLabels[index].identifier) == 0)
        return static_cast<IPresetHandler::PresetType>(index);
  }
  return IPresetHandler::Scene;
}

void MixerClientComponentBase::getPresetType(
    IPresetHandler::PresetType type, Core::CStringBuffer<128> &label) const {
  const auto *entry = findPresetLabel(type);
  label = entry ? entry->typeName : "";
}

void MixerClientComponentBase::getSuggestedPresetName(
    IPresetHandler::PresetType type, Core::CStringBuffer<128> &label) const {
  const auto *entry = findPresetLabel(type);
  label = entry ? entry->suggestion : "";
}
int MixerClientComponentBase::getNumPresets(IPresetHandler::PresetType type,
                                            const char *) const {
  const auto slot = static_cast<unsigned>(type);
  if (slot >= state_.presetRosters.size())
    return 0;
  const auto *roster = state_.presetRosters[slot];
  return roster ? roster->count() : 0;
}

IPresetHandler::Preset *
MixerClientComponentBase::getPreset(IPresetHandler::PresetType type, int index,
                                    const char *) const {
  const auto slot = static_cast<unsigned>(type);
  if (slot >= state_.presetRosters.size())
    return nullptr;
  const auto *roster = state_.presetRosters[slot];
  if (index >= (roster ? roster->count() : 0))
    return nullptr;
  if (index < 0)
    return PortableMixerState::PresetRoster::getError();
  return roster->at(index);
}

void MixerClientComponentBase::getRemotePresetTarget(
    IPresetHandler::PresetType type, Core::CStringBuffer<256> &target) {
  if (type == IPresetHandler::Scene)
    target.empty();
  else if (type == IPresetHandler::Channel)
    if (const auto *channel = getSelectedChannel())
      channel->getComponentPath(target);
}

} // namespace Presonus
