#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus::Surface {
int MidiMixerHandler::countMappings() const { return state_.mappingCount; }
const char *MidiMixerHandler::getName() const { return "midimixer"; }
bool MidiMixerHandler::canActivate() const { return state_.activeMapping >= 0; }
int MidiMixerHandler::getActiveMapping() const { return state_.activeMapping; }
void MidiMixerHandler::setActiveMapping(int value) {
  state_.activeMapping = value;
}
} // namespace Presonus::Surface
