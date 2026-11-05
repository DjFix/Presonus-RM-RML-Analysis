#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/MappingTable.hpp"
namespace Presonus::Surface {
void MidiMixerHandler::updateMapping(const MappingItem *items) {
  auto *normal = state_.normalParameters;
  auto *alternate = state_.alternateParameters;
  for (auto *item = items; item->name[0]; ++item) {
    auto *component = item->alternate ? alternate : normal;
    auto *parameter =
        item->tag == 0xffff ? nullptr : component->getParameterByTag(item->tag);
    state_.mappingTable->connect(item->name, parameter, nullptr, false);
    if (item->color)
      state_.mappingTable->setControlColor(item->name, item->color);
    if (item->disable)
      state_.mappingTable->setControlEnabled(item->name, false);
  }
}
bool MidiMixerHandler::getParamFocusInfo(
    Presonus::MixerAssignmentHandler::FocusInfo &,
    Core::Portable::Parameter *) {
  return false;
}
void MidiMixerHandler::connect() { setControlsEnabled(false); }
void MidiMixerHandler::resetColors() {
  for (std::size_t i = 0; i < state_.colorControls.size(); ++i) {
    if (state_.colorControls[i].empty())
      break;
    services_.setDefaultColor(state_.colorControls[i]);
  }
}
const char *MidiMixerHandler::getMappingName(int) {
  return state_.enabled ? "MCU over MIDI" : "";
}
void MidiMixerHandler::resetAccumulation() { state_.accumulation.fill(0); }
void MidiMixerHandler::updateRecordReadyMappings() {
  const bool vpot = services_.recordParameterPresent() &&
                    services_.recordParameterValue() != 0.0f;
  services_.updateRecordMapping(vpot);
}
void MidiMixerHandler::onIdle() {
  if (services_.idleSlotPresent(0))
    services_.invokeIdleSlot(0);
  if (services_.idleSlotPresent(1))
    services_.invokeIdleSlot(1);
}
} // namespace Presonus::Surface
