#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/MappingTable.hpp"
namespace Presonus::Surface {
void MidiMixerHandler::paramChanged(Core::Portable::Parameter *parameter, int) {
  const int tag = parameter->getTag();
  if (tag == 0) {
    updateRecordReadyMappings();
    return;
  }
  if (tag != 4 && tag != 5 && tag != 0xa007)
    return;
  // Upstream typed casting replaces the original compiler RTTI boundary.
  auto *stringParameter = Core::Portable::StringParam::cast(parameter);
  if (!stringParameter)
    return;
  auto *mode = state_.localParameters->getParameterByTag(5);
  const char *last = ":";
  const char *separator = ":";
  if (mode && mode->getValue() != 0.0f) {
    last = "\'";
    separator = ".";
  }
  // A second live lookup is observable if the first getValue mutates state.
  mode = state_.localParameters->getParameterByTag(5);
  if (mode && mode->getValue() != 0.0f) {
    last = "\'";
    separator = ":";
  }
  auto *output = state_.localParameters->getParameterByTag(2);
  Core::CString256 text = stringParameter->getText();
  text.insert(3, separator);
  text.insert(6, separator);
  text.insert(9, last);
  output->fromString(text.str(), false);
}

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
