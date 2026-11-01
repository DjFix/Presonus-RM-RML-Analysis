#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus::Surface {
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
