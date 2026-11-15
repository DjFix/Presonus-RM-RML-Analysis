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

namespace Presonus::Storm {
// _ZN8Presonus5StormL14gChSelectTableE; full original data range hash
// ed5af422c72f980e976fb2dcad4c2f211ecbf81463105f8da50992fa0f0822ed.
static const int gChSelectTable[] = {
    0,     1,     2,     3,     4,     5,  6,  7,  8,  9,  10,    11,
    12,    13,    14,    15,    16,    17, 18, 19, 20, 21, 22,    23,
    24,    25,    26,    27,    28,    29, 30, 31, 55, 56, 65527, 65527,
    65527, 65527, 65527, 65527, 65527, -1, 0,  0,  0};
// _ZN8Presonus5StormL17gChSelectOutTableE; full original data range hash
// 5f1cbe1bb9cdd24fc1acf14d2a640f3ad4faa3cf7957208928683eee3423da22.
static const int gChSelectOutTable[] = {32, 33, 34, 35, 36, 37, 38, 39, 40,
                                        41, 42, 43, 44, 45, 51, 52, 53, 54,
                                        46, 47, 48, 49, 50, -1, 0};
// _ZN8Presonus5StormL10gSoloTableE; full original data range hash
// d7b5b70bc1414c0d58814f2eb60fe66c85fee5bb107145733c48935e01f90dc7.
static const int gSoloTable[] = {
    0,     1,     2,     3,     4,     5,  6,  7,  8,     9,     10,    11,
    12,    13,    14,    15,    16,    17, 18, 19, 20,    21,    22,    23,
    24,    25,    26,    27,    28,    29, 30, 31, 65527, 65527, 65527, 65527,
    65527, 65527, 65527, 65527, 65527, -1, 0,  0,  0};
// _ZN8Presonus5StormL13gSoloOutTableE; full original data range hash
// b80783e07325dad4ffc79c00d7f9fbffc5bf02629bb217ed341a8fa9e8f18887.
static const int gSoloOutTable[] = {
    32, 33,    34,    35,    36,    37, 38, 39, 40, 41,    42, 43, 44,
    45, 65527, 65527, 65527, 65527, 46, 47, 48, 49, 65527, -1, 0};
// _ZN8Presonus5StormL12gChMuteTableE; full original data range hash
// d7b5b70bc1414c0d58814f2eb60fe66c85fee5bb107145733c48935e01f90dc7.
static const int gChMuteTable[] = {
    0,     1,     2,     3,     4,     5,  6,  7,  8,     9,     10,    11,
    12,    13,    14,    15,    16,    17, 18, 19, 20,    21,    22,    23,
    24,    25,    26,    27,    28,    29, 30, 31, 65527, 65527, 65527, 65527,
    65527, 65527, 65527, 65527, 65527, -1, 0,  0,  0};
// _ZN8Presonus5StormL15gChMuteOutTableE; full original data range hash
// 02352b8b2a853b742981cde3dc400d2e83d0645196891820e14ac273456465f4.
static const int gChMuteOutTable[] = {32, 33, 34, 35, 36,    37, 38, 39, 40,
                                      41, 42, 43, 44, 45,    46, 47, 48, 49,
                                      50, 51, 52, 53, 65527, -1, 0};
} // namespace Presonus::Storm
namespace Presonus::Panel {
void StormFrontPanelComponent::getTablesForGroup(int group, const int *&first,
                                                 const int *&second,
                                                 int &count) const {
  switch (group) {
  case 0:
    first = Presonus::Storm::gChSelectTable;
    second = Presonus::Storm::gChSelectOutTable;
    count = 13;
    break;
  case 1:
    first = Presonus::Storm::gSoloTable;
    second = Presonus::Storm::gSoloOutTable;
    count = 14;
    break;
  case 2:
    first = Presonus::Storm::gChMuteTable;
    second = Presonus::Storm::gChMuteOutTable;
    count = 18;
    break;
  default:
    break;
  }
}
} // namespace Presonus::Panel
