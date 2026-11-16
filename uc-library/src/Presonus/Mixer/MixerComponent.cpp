#include "presonus/mixer/MixerComponent.hpp"
#include "core/portable/corepersistence.h"
#include "core/system/coredebug.h"
#include "presonus/mixer/DigitalInputComponent.hpp"
#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <cstring>
#include <stdexcept>

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
void MixerComponent::doLink(GEQComponent *equalizer, bool link) {
  if (state_.equalizers.isEmpty())
    return;
  Presonus::LinkableComponent *target = nullptr;
  bool bound = false;
  for (int i = 0; i < state_.geqLinkIdentities.count(); ++i) {
    const auto &entry = state_.geqLinkIdentities.at(i);
    if (entry.equalizer == equalizer) {
      target = entry.linkable;
      bound = true;
      break;
    }
  }
  if (!bound || !target)
    throw std::logic_error("GEQ link identity is unbound");
  auto *partner = getGeqLinkPartner(target);
  if (!partner)
    return;
  if (link)
    target->setLink(*partner, false);
  else
    target->removeLink();
}
void MixerComponent::panicMuteAll(bool mute) {
  if (mute) {
    for (int i = 0; i < state_.channels.count(); ++i) {
      auto *parameter = state_.channels.at(i)->portableState().mute;
      if (parameter && parameter->getValue() == 0.f) {
        rememberMutes(state_.panicMutes, MixerComponentBase::Filter{1});
        for (int j = 0; j < state_.channels.count(); ++j)
          if (auto *target = state_.channels.at(j)->portableState().mute)
            target->setValue(1.f, false);
        return;
      }
    }
    state_.panicMutes.removeAll();
  } else if (!state_.panicMutes.isEmpty()) {
    restoreMutes(state_.panicMutes, MixerComponentBase::Filter{1});
  } else {
    for (int i = 0; i < state_.channels.count(); ++i)
      if (auto *target = state_.channels.at(i)->portableState().mute)
        target->setValue(0.f, false);
  }
}
void MixerComponent::sendStageboxSceneMsg(const char *id, const char *component,
                                          int slot) {
  if (!state_.stageboxNetwork)
    return;
  if (!state_.stageboxOrigins)
    throw std::logic_error("Stagebox message provenance is unbound");
  UC::MessageAttributes attributes(id);
  attributes.setURL("presets");
  attributes.set("AVBSceneSlot", static_cast<Core::int64>(slot));
  attributes.set("AVBMComponentID", component, false);
  UC::MutableMessageEvent message(attributes, 0x4a4d, 0);
  // Copy the complete nonowning typed view, retaining the real owning Buffer
  // and provenance binding through synchronous forwarding. Never copy just the
  // header or cast away constness from the source-port accessor.
  UC::MessageEvent outgoing =
      presonus::uc::MutableMessageEventPortAccess::event(message);
  auto binding = state_.stageboxOrigins->bind(outgoing);
  if (!binding)
    throw std::logic_error("Stagebox message type cannot be bound");
  state_.stageboxNetwork->sendEvent(outgoing.header);
}
void MixerComponent::doSelect(ChannelComponent *channel) {
  const presonus::mixer_component_port::MixerState::ChannelLinkIdentity
      *identity = nullptr;
  for (int i = 0; i < state_.channelLinks.count(); ++i)
    if (state_.channelLinks.at(i).channel == channel) {
      identity = &state_.channelLinks.at(i);
      break;
    }
  if (!identity || !identity->linkable || !identity->state)
    throw std::logic_error("Channel link identity is unbound");
  if (identity->linkable->isLinkSlave() && state_.selectionGuard)
    return;
  Core::DebugPrintf("MixerComponent::doSelect...\n");
  state_.selectedChannel = channel;
  // Preserve the recorded existing flag ordering: selected→native0x11a,
  // dirty→native0x36a. Historical cascade cases set both; semantic names and
  // unequal-value correspondence remain a source-port adaptation.
  if (state_.cascadeDirty)
    state_.cascadeSelected = true;
  state_.cascadeDirty = false;
  ChannelComponent *partner = nullptr;
  if (identity->state->partner)
    for (int i = 0; i < state_.channelLinks.count(); ++i)
      if (state_.channelLinks.at(i).linkable == identity->state->partner) {
        partner = state_.channelLinks.at(i).channel;
        break;
      }
  auto *current = state_.selectedChannel;
  const int count = state_.channels.count();
  auto *channels = state_.channels.getItems();
  for (int i = 0; i < count; ++i) {
    if (channels[i] == partner || channels[i] == current)
      continue;
    services_.selection(*channels[i]).setValue(0.f, false);
    current = state_.selectedChannel;
  }
  if (current) {
    services_.selection(*current).setValue(1.f, false);
    services_.selection(*state_.selectedChannel).changed();
  }
  if (partner)
    services_.selection(*partner).setValue(1.f, false);
  if (state_.delegates) {
    const int count = state_.delegates->count();
    auto *items = state_.delegates->getItems();
    for (int i = 0; i < count; ++i)
      items[i]->selectionChanged();
  } else {
    const int observers = state_.selectionObservers.count();
    auto *items = state_.selectionObservers.getItems();
    for (int i = 0; i < observers; ++i)
      items[i]->selectionChanged();
  }
}
void MixerComponent::onAVBListenerChange() {
  const auto notify = [](const Core::Vector<ChannelComponent *> *channels,
                         int tag) {
    if (!channels)
      return;
    const int count = channels->count();
    auto *items = channels->getItems();
    for (int i = 0; i < count; ++i)
      if (auto *parameter = items[i]->getParameterByTag(tag))
        parameter->changed();
  };
  notify(state_.avbListeners.parameter304Channels, 304);
  if (auto *channels = state_.avbListeners.digitalInputCandidates) {
    const int count = channels->count();
    auto *items = channels->getItems();
    for (int i = 0; i < count; ++i) {
      if (dynamic_cast<DigitalInputComponent *>(items[i])) {
        if (auto *parameter = items[i]->getParameterByTag(360))
          parameter->changed();
        break;
      }
    }
  }
  notify(state_.avbListeners.parameter340Channels, 340);
}
void MixerComponent::doLink(ChannelComponent *channel, bool link) {
  const presonus::mixer_component_port::MixerState::ChannelLinkIdentity
      *identity = nullptr;
  for (int i = 0; i < state_.channelLinks.count(); ++i)
    if (state_.channelLinks.at(i).channel == channel) {
      identity = &state_.channelLinks.at(i);
      break;
    }
  if (!identity || !identity->linkable)
    throw std::logic_error("Channel link identity is unbound");
  const Core::Vector<ChannelComponent *> *channels = nullptr;
  switch (identity->kind) {
  case 0:
  case 2:
  case 3:
    channels = state_.linkKind0To3;
    break;
  case 4:
    channels = state_.linkKind4;
    break;
  case 6:
    channels = state_.linkKind6;
    break;
  default:
    return;
  }
  if (!channels)
    throw std::logic_error("Channel link collection is unbound");
  auto *partner = getLinkPartner(identity->linkable, *channels);
  if (!partner)
    return;
  if (!state_.delegates && !state_.selectionObservers.isEmpty())
    throw std::logic_error(
        "Legacy selection callbacks do not bind link delegates");
  state_.selectionGuard = true;
  if (link) {
    Presonus::LinkableComponent *partnerIdentity = nullptr;
    for (int i = 0; i < state_.channelLinks.count(); ++i)
      if (state_.channelLinks.at(i).channel == partner) {
        partnerIdentity = state_.channelLinks.at(i).linkable;
        break;
      }
    if (!partnerIdentity)
      throw std::logic_error("Partner link identity is unbound");
    identity->linkable->setLink(*partnerIdentity, false);
  } else {
    // Exact native Channel primary slot0x40 overrides Linkable::removeLink.
    channel->removeLink();
  }
  channel->getParameterByTag(21)->setValue(link ? 1.f : 0.f, false);
  partner->getParameterByTag(21)->setValue(link ? 1.f : 0.f, false);
  if (state_.delegates) {
    const int count = state_.delegates->count();
    auto *items = state_.delegates->getItems();
    for (int i = 0; i < count; ++i)
      items[i]->linkChanged();
  }
  state_.selectionGuard = false;
  if (identity->kind == 4 && state_.linkPermissions)
    state_.linkPermissions->auxLinkingChanged();
}
} // namespace Presonus::Mixer
