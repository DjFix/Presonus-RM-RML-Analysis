#include "presonus/mixer/RackMixerComponent.hpp"
#include "core/public/corestringbuffer.h"
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
} // namespace Presonus::Mixer
