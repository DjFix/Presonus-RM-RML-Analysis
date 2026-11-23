#include "presonus/mixer/RackMixerComponent.hpp"
#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/mixer/DigitalInputComponent.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include "presonus/noaa/card_handler.hpp"
#include <new>
#include <stdexcept>
namespace Presonus::Mixer {
void RackMixerComponent::lineSenseChanged(
    const Presonus::Panel::ControlRegistrar &, int lineIndex, int senseValue) {
  const auto hardware = base_.numHWMicLineIn();
  const auto count = base_.inputChannels.count();
  if (count == 0)
    return;
  const std::uint32_t index =
      static_cast<std::uint32_t>(lineIndex) - 8u + hardware;
  if ((index & 0x80000000u) || index >= static_cast<std::uint32_t>(count))
    return;
  if (auto *channel = base_.inputChannels.at(static_cast<int>(index)))
    if (auto *parameter = channel->getParameterByTag(313))
      parameter->setValue(senseValue > 0 ? 1.f : 0.f, false);
}

bool RackMixerComponent::supportSubgroupMode() const { return true; }

void RackMixerComponent::onCascadeStateChange() {
  base_.onCascadeStateChange();
  if (!base_.isSlave())
    cascadeState_ = 0;
}
void RackMixerComponent::setupAllMutesGroup() {
  if (!base_.sceneChannels || base_.sceneChannels->isEmpty())
    return;
  if (!muteGroups || !base_.channelIdentity)
    throw std::logic_error("all-mutes group binding required");
  auto &members = muteGroups->allMutes;
  for (int i = 0; i < base_.sceneChannels->count(); ++i) {
    auto *channel = base_.sceneChannels->at(i);
    if (!channel)
      throw std::logic_error("all-mutes channel is null");
    const auto kind = base_.channelIdentity(channel).first;
    if (kind != 0 && kind != 6 && kind != 2 && kind != 1 && kind != 4 &&
        kind != 5)
      continue;
    auto *mute = channel->portableState().mute;
    if (!mute)
      continue;
    try {
      if (members.count() >= members.getCapacity() &&
          !members.resize(members.count() + 1))
        continue;
      members.add(mute);
    } catch (const std::bad_alloc &) {
      // CCL throwing allocation maps to native false resize; continue scanning.
    }
  }
}
void RackMixerComponent::buildAuxRouteList(Core::Portable::ListParam &list) {
  list.removeAll();
  list.appendString("Main Mix L/R");
  list.appendString("Main Mix Mono/Center");
  for (std::int32_t i = 1; i < auxiliaryRouteCount; i += 2) {
    Core::CString128 text;
    text.appendFormat("Aux Send %d-%d", i, i + 1);
    list.appendString(text.str());
  }
  list.appendString("FX Send A-B");
  list.appendString("FX Send C-D");
  list.appendString("Tape In");
  list.appendString("Solo L/R");
  list.appendString("Talkback");
  list.rangeChanged();
}
void RackMixerComponent::getTDMRoutes(int selection, unsigned char &left,
                                      unsigned char &right,
                                      unsigned int &mode) {
  mode = 4;
  if (selection >= 2 && selection <= 9) {
    left = static_cast<unsigned char>(selection * 2 + 38);
    right = static_cast<unsigned char>(left + 1);
    return;
  }
  switch (selection) {
  case 0:
    left = 60;
    right = 61;
    break;
  case 1:
    left = 58;
    right = 58;
    break;
  case 10:
    left = 32;
    right = 33;
    break;
  case 11:
    left = 34;
    right = 35;
    break;
  case 12:
    left = 38;
    right = 39;
    mode = 0;
    break;
  case 13:
    left = 62;
    right = 63;
    break;
  case 14: {
    mode = 0;
    ChannelComponent *channel =
        base_.inputChannels.count() > 0 ? base_.inputChannels.at(0) : nullptr;
    if (auto *talkback = dynamic_cast<TalkbackInputComponent *>(channel)) {
      const TalkbackRouteState *binding = nullptr;
      for (const auto &entry : talkbackRoutes)
        if (entry.identity == talkback) {
          binding = &entry;
          break;
        }
      if (!binding)
        throw std::logic_error("Talkback routing state is unbound");
      left = static_cast<unsigned char>(binding->route);
      mode = binding->mode;
    }
    if (left == 255)
      left = 36;
    right = left;
    break;
  }
  default:
    break;
  }
}
void RackMixerComponent::setDanteStaticRoutes() {
  if (!danteHandler || !danteSourceChannels || !danteEffects)
    throw std::logic_error("Dante route providers are unbound");
  const auto first = static_cast<std::uint32_t>(danteSourceChannels->count());
  const auto auxiliary = static_cast<std::uint32_t>(auxiliaryRouteCount);
  const auto effects = static_cast<std::uint32_t>(danteEffects->count());
  Core::DebugPrintf("**************** micline #%d\n",
                    danteSourceChannels->count());
  const auto route = [&](std::uint32_t destination, std::uint32_t source,
                         std::uint32_t count) {
    Core::Property property(0x64746e70, 24);
    const presonus::noaa::ImmediatePropertyProjection projection{
        &property, {0, destination, source, count, 0}};
    auto &handlerState = danteHandler->portableHandlerState();
    const auto *previous = handlerState.immediate;
    handlerState.immediate = &projection;
    try {
      danteHandler->setProperty(property);
    } catch (...) {
      handlerState.immediate = previous;
      throw;
    }
    handlerState.immediate = previous;
  };
  std::uint32_t destination = first;
  route(destination, 60, 1);
  ++destination;
  route(destination, 58, 1);
  ++destination;
  route(destination, 61, 1);
  ++destination;
  route(destination, 42, auxiliary);
  destination += auxiliary;
  route(destination, 32, effects);
  destination += effects;
  route(destination, 62, 2);
  destination += 2;
  route(destination, first - 1u, 1);
  if (digitalInputCandidates) {
    const int count = digitalInputCandidates->count();
    auto *items = digitalInputCandidates->getItems();
    for (int i = 0; i < count; ++i) {
      if (dynamic_cast<DigitalInputComponent *>(items[i])) {
        if (auto *parameter = items[i]->getParameterByTag(360))
          parameter->changed();
        break;
      }
    }
  }
}
} // namespace Presonus::Mixer
