#include "presonus/surface/DAWMixerHandler.hpp"
#include "presonus/ColorMapping.hpp"
#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"
#include "presonus/DAWClientComponent.hpp"
#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/surface/PageParam.hpp"
#include <cstring>

namespace Presonus::Surface {
DAWMixerHandler::DAWMixerHandler(
    presonus::surface::DAWMixerDependencies &dependencies,
    presonus::surface::DAWMixerState &state)
    : dependencies(dependencies), state(state), ownedAutomation(std::in_place),
      automation(*ownedAutomation) {}

DAWMixerHandler::~DAWMixerHandler() = default;

int DAWMixerHandler::getSelectedMix() const {
  const int value = state.mappingController
                        ? state.mappingController->getRadioValue(13, 33)
                        : -1;
  return value < 0 ? 33 : value;
}
int DAWMixerHandler::getSelectedMeterMode() const {
  return state.mappingController
             ? state.mappingController->getRadioValue(34, 37)
             : -1;
}

void DAWMixerHandler::getMixTargets(MixTargets &targets, DAWChannel *channel,
                                    int mix) const {
  if (!channel)
    return;
  auto parameter = [](Core::Portable::Component *component, int tag) {
    return component ? component->getParameterByTag(tag) : nullptr;
  };
  if (mix >= 21 && mix <= 28) {
    auto *folder = state.client ? channel->getCueMixes()
                                : dependencies.folder(channel, true);
    if (!folder || mix - 21 >= (state.client ? folder->getUsedCount()
                                             : dependencies.usedCount(folder)))
      return;
    auto *slot = (state.client ? folder->getChild(mix - 21)
                               : dependencies.slot(folder, mix - 21));
    if (!slot)
      return;
    targets.level = parameter(slot, 1);
    targets.mute = parameter(slot, 2);
    targets.pan = parameter(slot, 3);
    return;
  }
  auto *component = state.client ? channel : dependencies.component(channel);
  if (mix >= 13 && mix <= 20) {
    auto *folder = state.client ? channel->getSends()
                                : dependencies.folder(channel, false);
    if (folder && mix - 13 < (state.client ? folder->getUsedCount()
                                           : dependencies.usedCount(folder))) {
      if (auto *slot = (state.client ? folder->getChild(mix - 13)
                                     : dependencies.slot(folder, mix - 13)))
        targets.level = parameter(slot, 1);
    }
  } else if (mix == 33) {
    targets.level = parameter(component, 8);
    const char *type =
        state.client ? channel->getType() : dependencies.channelType(channel);
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
void DAWMixerHandler::setController(Presonus::IMappingController *controller) {
  state.mappingController = controller;
  for (DawFxPageComponent &page : state.dawPages)
    page.setMappingController(controller);
  if (state.mappingController)
    state.mappingController->setRadioGroup(34, 34, 37, false);
}

void DAWMixerHandler::updatePanEncoderConnection() {
  auto *channel =
      state.client
          ? state.client->getFocusChannel()
          : (state.clientPresent ? dependencies.focusChannel() : nullptr);
  MixTargets targets;
  getMixTargets(targets, channel,
                state.client ? getSelectedMix() : dependencies.selectedMix());
  if (targets.mute && !targets.mute->isEnabled())
    targets.mute = nullptr;
  if (state.client && state.mappingTable)
    state.mappingTable->connect("display_pan_encoder", targets.mute, nullptr,
                                false);
  else
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
bool DAWMixerHandler::handleMappingRadioGroup(Core::Portable::Parameter *) {
  return false;
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
    auto *component = state.client ? channel : dependencies.component(channel);
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

namespace Presonus::Surface {
namespace {
Core::Portable::Parameter *byTag(Core::Portable::Component *component,
                                 int tag) {
  return component ? component->getParameterByTag(tag) : nullptr;
}
DAWChannel *channelAt(DAWChannelGroup *group, int index) {
  auto *child = group && index >= 0 && index < group->countChildren()
                    ? group->getChild(index)
                    : nullptr;
  return child ? static_cast<DAWChannel *>(child->castTo(0x44617743)) : nullptr;
}
Core::CStringBuffer<32> stripName(const char *prefix, int index) {
  Core::CStringBuffer<32> name;
  name.appendFormat("%s_%02d", prefix, index);
  return name;
}
constexpr const char *controlNames[] = {
    "fatch_in_48V",     "fatch_in_phase", "fatch_gate_on",
    "fatch_gate_edit",  "fatch_comp_on",  "fatch_comp_edit",
    "fatch_limiter_on", "fatch_eq_on",    "fatch_eq_edit"};
} // namespace
DAWChannel *DAWMixerHandler::getMainChannel() {
  if (!state.client || !state.mainGroup || state.mainGroup->getUsedCount() <= 0)
    return nullptr;
  return channelAt(state.mainGroup, 0);
}
void DAWMixerHandler::assignControlLinkTargets() {
  if (!state.mappingTable)
    return; // Explicit unassembled source-port state, not a native null-table
            // claim.
  auto &table = *state.mappingTable;
  auto *controls = state.client ? state.client->getControlLink() : nullptr;
  if (!controls || !state.stripMeters) {
    for (const char *name : controlNames)
      table.connect(name, nullptr, nullptr, false);
    for (int i = 1; i <= 16; ++i)
      table.connect(stripName("scribble_encoderInfo", i), nullptr, nullptr,
                    false);
    return;
  }
  for (int i = 0; i < 25; ++i) {
    Core::CStringBuffer<32> childName;
    childName.appendFormat("p%d", i);
    auto *child = controls->findChild(childName);
    if (i < 16) {
      auto *value = byTag(child, 0);
      table.connect(stripName("strip_encoder", i + 1), value, nullptr, false);
      table.connect(stripName("scribble_encoderInfo", i + 1), byTag(child, 2),
                    nullptr, false);
      table.connect(stripName("strip_meter", i + 1), value, "meter-single-seg",
                    false);
      table.connect(stripName("strip_clip", i + 1), nullptr, nullptr, false);
    } else
      table.connect(controlNames[i - 16], byTag(child, 0), nullptr, false);
  }
}
void DAWMixerHandler::assignSelectedChannelTargets() {
  if (!state.mappingController || !state.client || !state.mappingTable)
    return;
  auto *channel = state.client->getFocusChannel();
  auto &table = *state.mappingTable;
  table.connect("selch_meter", byTag(channel, 1000), "meter-audio-no-taper",
                false);
  table.connect("selch_comp_meter", byTag(channel, 21), "meter-bar-reverse",
                false);
  table.connect("chan_stereo_link", byTag(channel, 10), nullptr, false);
  for (const auto &entry : {std::pair<const char *, int>{"channel_name", 3},
                            {"channel_info", 3},
                            {"channel_number", 4}}) {
    PageParam route("header", entry.first);
    table.connect(route.c_str(), byTag(channel, entry.second), nullptr, false);
  }
  if (!state.mappingController->isDisplayEncoderLocked())
    updatePanEncoderConnection();
  syncAutomationParams(channel);
}
void DAWMixerHandler::assignStripTargets(DAWChannelGroup *group, int offset,
                                         const char *filter) {
  if (!state.mappingTable)
    return;
  auto &table = *state.mappingTable;
  Core::CStringBuffer<64> groupFilter(filter ? filter : "");
  const bool negate = std::strstr(groupFilter, "not") == groupFilter.str();
  int index = groupFilter.isEmpty() ? offset : 0;
  auto next = [&]() -> DAWChannel * {
    while (group && index < group->getUsedCount()) {
      auto *child = index >= 0 && index < group->countChildren()
                        ? group->getChild(index)
                        : nullptr;
      ++index;
      if (!child)
        return nullptr;
      auto *channel = static_cast<DAWChannel *>(child->castTo(0x44617743));
      if (!channel || groupFilter.isEmpty())
        return channel;
      const char *type = channel->getType();
      const bool contains =
          std::strstr(groupFilter, type ? type : "") != nullptr;
      if (negate != contains)
        return channel;
    }
    return nullptr;
  };
  if (!groupFilter.isEmpty())
    for (int skipped = 0; skipped < offset; ++skipped)
      next();
  const int mix = getSelectedMix();
  const int meterMode = getSelectedMeterMode();
  for (int strip = 1; strip <= 16; ++strip) {
    auto *channel = next();
    MixTargets targets;
    getMixTargets(targets, channel, mix);
    const char *names[] = {"strip_fader",    "scribble_pan",  "strip_mute",
                           "strip_solo",     "strip_select",  "scribble_number",
                           "scribble_label", "scribble_info", "scribble_arm"};
    Core::Portable::Parameter *parameters[] = {
        targets.level,
        targets.mute,
        targets.pan,
        targets.extraPan,
        byTag(channel, state.shift ? 17 : 6),
        byTag(channel, 4),
        byTag(channel, 3),
        byTag(channel, 18),
        byTag(channel, 17)};
    for (int i = 0; i < 9; ++i)
      table.connect(stripName(names[i], strip), parameters[i], nullptr, false);
    if (!state.stripMeters) {
      table.connect(stripName("strip_meter", strip),
                    byTag(channel, meterMode == 36 ? 21 : 1000),
                    channel && meterMode == 36 ? "meter-bar-reverse"
                                               : "meter-audio-no-taper",
                    false);
      table.connect(stripName("strip_clip", strip),
                    meterMode == 36 ? nullptr : byTag(channel, 13), nullptr,
                    false);
      table.connect(stripName("strip_encoder", strip), targets.mute, nullptr,
                    false);
    }
    const char *colorName = "green";
    auto *color = Core::Portable::ColorParam::cast(byTag(channel, 5));
    if (color) {
      // Real typed provider, as in MixerColorConverter. Legacy MappingTable's
      // int callback result cannot encode the native name pointer on Linux.
      colorName = Presonus::ColorMapping::mapColor(
          Core::Color::fromInt(color->getColor()));
    }
    table.setControlColor(stripName("strip_select", strip), colorName);
  }
}
void DAWMixerHandler::assignChannels() {
  if (!state.mappingController || !state.client)
    return;
  auto &controller = *state.mappingController;
  int offset = controller.getBankScrollingOffset();
  int radio = controller.getRadioValue(0, 6);
  if (radio >= 0) {
    int width = radio <= 3 ? 64 : 16;
    int modifiers = controller.getModifiers();
    if (modifiers & 2)
      offset += width;
    if (modifiers & 1)
      offset += 2 * width;
  }
  auto enabled = [&](int tag) {
    auto *parameter = controller.getParamByTag(tag);
    return parameter && parameter->getValue() > 0;
  };
  auto *group = state.inputGroup;
  Core::CStringBuffer<64> filter;
  if (enabled(4))
    filter = "AudioEffect";
  else if (enabled(5))
    filter = "AudioGroup";
  else if (enabled(6))
    group = state.outputGroup;
  else {
    filter = "not ";
    filter.append("AudioEffect");
    filter.append("AudioGroup");
  }
  assignStripTargets(group, offset, filter);
  assignSelectedChannelTargets();
}
} // namespace Presonus::Surface
