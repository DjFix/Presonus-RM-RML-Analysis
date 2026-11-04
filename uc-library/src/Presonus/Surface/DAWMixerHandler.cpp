#include "presonus/surface/DAWMixerHandler.hpp"
#include <cstring>

namespace Presonus::Surface {
void DAWMixerHandler::getMixTargets(MixTargets &targets, DAWChannel *channel,
                                    int mix) const {
  if (!channel)
    return;
  auto parameter = [](Core::Portable::Component *component, int tag) {
    return component ? component->getParameterByTag(tag) : nullptr;
  };
  if (mix >= 21 && mix <= 28) {
    auto *folder = dependencies.folder(channel, true);
    if (!folder || mix - 21 >= dependencies.usedCount(folder))
      return;
    auto *slot = dependencies.slot(folder, mix - 21);
    if (!slot)
      return;
    targets.level = parameter(slot, 1);
    targets.mute = parameter(slot, 2);
    targets.pan = parameter(slot, 3);
    return;
  }
  auto *component = dependencies.component(channel);
  if (mix >= 13 && mix <= 20) {
    auto *folder = dependencies.folder(channel, false);
    if (folder && mix - 13 < dependencies.usedCount(folder)) {
      if (auto *slot = dependencies.slot(folder, mix - 13))
        targets.level = parameter(slot, 1);
    }
  } else if (mix == 33) {
    targets.level = parameter(component, 8);
    const char *type = dependencies.channelType(channel);
    if (!type || std::strcmp(type, "AudioOutput") != 0)
      targets.mute = parameter(component, 9);
    targets.pan = parameter(component, 14);
    targets.extraPan = parameter(component, 15);
    return;
  } else
    return;
  targets.mute = parameter(component, 9);
  targets.pan = parameter(component, 14);
  targets.extraPan = parameter(component, 15);
}
void DAWMixerHandler::updatePanEncoderConnection() {
  auto *channel = state.clientPresent ? dependencies.focusChannel() : nullptr;
  MixTargets targets;
  getMixTargets(targets, channel, dependencies.selectedMix());
  if (targets.mute && !targets.mute->isEnabled())
    targets.mute = nullptr;
  dependencies.connect("display_pan_encoder", targets.mute, nullptr, false);
}
void DAWMixerHandler::assignMainChannel() {
  auto *channel = dependencies.mainChannel();
  auto *component = channel ? dependencies.component(channel) : nullptr;
  constexpr const char *names[] = {"main_mono_meter", "main_left_meter",
                                   "main_right_meter", "main_fader",
                                   "main_select"};
  constexpr int tags[] = {1000, 11, 12, 8, 6};
  for (int i = 0; i != 5; ++i) {
    auto *parameter =
        component ? component->getParameterByTag(tags[i]) : nullptr;
    dependencies.connect(names[i], parameter,
                         i < 3 ? "meter-audio-no-taper" : nullptr, false);
  }
  dependencies.connect("mono_select", nullptr, nullptr, false);
}
void DAWMixerHandler::onChannelsChanged(DAWChannelGroup *group) {
  if (!state.clientPresent || !state.mappingController)
    return;
  if (group == state.mainGroup)
    assignMainChannel();
  else if (group == state.inputGroup || group == state.outputGroup)
    dependencies.assignChannels();
}
void DAWMixerHandler::onChannelParamChanged(
    DAWChannel *channel, Core::Portable::Parameter *parameter) {
  switch (parameter->getTag()) {
  case 0:
  case 5:
    dependencies.assignChannels();
    break;
  case 22:
    if (state.channelNamesVisible)
      dependencies.assignFlexStrip();
    break;
  case 18:
    if (channel == dependencies.focusChannel())
      syncAutomationParams(channel);
    break;
  default:
    break;
  }
}
void DAWMixerHandler::onModifiersChanged() {
  const auto shift = (state.mappingController->getModifiers() >> 2) & 1;
  if (state.shift == shift)
    return;
  state.shift = static_cast<std::uint8_t>(shift);
  dependencies.assignChannels();
}
void DAWMixerHandler::onMappingParamChanged(
    Core::Portable::Parameter *parameter) {
  const auto tag = static_cast<std::uint32_t>(parameter->getTag());
  if (tag <= 6 || tag - 13 <= 20) {
    dependencies.assignChannels();
    return;
  }
  if (tag - 34 > 3)
    return;
  const bool meters = dependencies.showStripMeters();
  if (state.stripMeters == meters) {
    dependencies.assignChannels();
    return;
  }
  state.stripMeters = static_cast<std::uint8_t>(meters);
  dependencies.assignChannels();
  dependencies.assignControlLinkTargets();
  if (state.stripMeters && state.mappingController) {
    if (auto *parameter = state.mappingController->getMainScreenParamByTag(18))
      parameter->setValue(1.f, true);
  }
}
void DAWMixerHandler::onFocusChannelChanged() {
  if (!state.mappingController)
    return;
  state.mappingController->onSelectedChannelChanged();
  dependencies.assignSelectedChannelTargets();
}
void DAWMixerHandler::onSlotCountChanged(DAWDeviceFolder *) {
  if (dependencies.selectedMix() != 33)
    dependencies.assignChannels();
}
void DAWMixerHandler::syncAutomationParams(DAWChannel *channel) {
  int selected = -1;
  if (channel) {
    auto *component = dependencies.component(channel);
    auto *parameter = component ? component->getParameterByTag(18) : nullptr;
    if (parameter)
      selected =
          static_cast<int>(static_cast<double>(parameter->getValue()) + 0.5);
  }
  for (int i = 0; i != 4; ++i)
    if (auto *parameter = automation.byTag(i))
      parameter->setValue(selected == i + 1 ? 1.f : 0.f, false);
}
} // namespace Presonus::Surface

#include "presonus/PageComponent.hpp"
#include "presonus/surface/DAWMixerHandler.hpp"
#include <cstdint>
namespace Presonus::Surface {
bool DAWMixerHandler::shouldShowStripEncodersAsMeters() const {
  const int mode = state.mappingController
                       ? state.mappingController->getRadioValue(34, 37)
                       : -1;
  return (static_cast<std::uint32_t>(mode) >> 31) != 0;
}
} // namespace Presonus::Surface
