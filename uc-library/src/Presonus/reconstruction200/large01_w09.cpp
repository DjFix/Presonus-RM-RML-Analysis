#include "presonus/reconstruction200/large01_w09.hpp"
#include <bit>
namespace Presonus::Surface {
MarkerPageComponent::~MarkerPageComponent() = default;
DAWDialogHandler::~DAWDialogHandler() = default;
DawFxPageComponent::~DawFxPageComponent() = default;
void DawFxPageComponent::setMappingController(
    Presonus::IMappingController *controller) {
  mappingController_ = controller;
}
int MarkerPageComponent::getMaxMarkerListOffset(TrackAccessor &track) const {
  if (!track.markerCount)
    return 0;
  auto count =
      std::bit_cast<std::int32_t>(std::uint32_t(*track.markerCount) - 1u);
  auto result = (count / 5) * 5;
  return result < 0 ? 0 : result;
}
int MidiMixerHandler::countMappings() const { return state_.mappingCount; }
const char *MidiMixerHandler::getName() const { return "midimixer"; }
bool MidiMixerHandler::canActivate() const { return state_.activeMapping >= 0; }
int MidiMixerHandler::getActiveMapping() const { return state_.activeMapping; }
void MidiMixerHandler::setActiveMapping(int value) {
  state_.activeMapping = value;
}
} // namespace Presonus::Surface
