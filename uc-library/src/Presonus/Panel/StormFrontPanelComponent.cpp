#include "presonus/panel/StormFrontPanelComponent.hpp"
namespace Presonus::Panel {
void StormFrontPanelComponent::cleanup() { dependencies.cleanup(); }
void StormFrontPanelComponent::mixSceneRecalled(
    const Presonus::StormMixSceneComponent &) {
  dependencies.presetRecalled();
}
void StormFrontPanelComponent::mixSceneEnterStoreState(
    const Presonus::StormMixSceneComponent &) {
  blinkSceneButtons(true);
}
void StormFrontPanelComponent::mixSceneExitStoreState(
    const Presonus::StormMixSceneComponent &) {
  blinkSceneButtons(false);
}
void StormFrontPanelComponent::setMuteGroupDirty(
    const Presonus::StormMuteGroupComponent &, int index, bool dirty) {
  dependencies.blinkLED(8, static_cast<std::uint32_t>(index) + 2U, dirty);
}
void StormFrontPanelComponent::setAllMutesGroupDirty(
    const Presonus::StormMuteGroupComponent &, bool dirty) {
  dependencies.blinkLED(8, 0, dirty);
}
void StormFrontPanelComponent::doFatChannelUpdate() {
  auto group = dependencies.findGroup(13);
  for (int tag = 24; tag != 32; ++tag)
    dependencies.setControl(dependencies.byTag(group, tag), 0, 0);
  dependencies.fatChannelUpdate();
}
MixerLCD *StormFrontPanelComponent::createLCD() {
  auto *lcd = dependencies.constructLCD(336);
  dependencies.addBook(lcd, 0x32b9d8, 7);
  dependencies.addBook(lcd, 0x32ba5c, 11);
  return lcd;
}
void StormFrontPanelComponent::doFatMeterUpdate(
    Presonus::Mixer::ChannelComponent &channel) {
  dependencies.fatMeterUpdate(channel);
  auto first = dependencies.findGroup(14);
  auto second = dependencies.findGroup(17);
  for (int tag = 24; tag != 32; ++tag) {
    dependencies.setControl(dependencies.byTag(first, tag), 0, 7);
    dependencies.setControl(dependencies.byTag(second, tag), 0, 0);
  }
}
void StormFrontPanelComponent::blinkSceneButtons(bool enabled) {
  auto group = dependencies.findGroup(9);
  int count = dependencies.count(group);
  for (int i = 0; i < count; ++i) {
    auto control = dependencies.at(group, i);
    if (!control)
      continue;
    auto led = dependencies.asLED(control);
    if (!led)
      continue;
    int tag = dependencies.tag(led);
    if (tag > 1 && tag <= 7)
      dependencies.setBlinkMode(led, enabled);
  }
}
} // namespace Presonus::Panel
