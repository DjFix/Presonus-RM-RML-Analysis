#include "presonus/MappingTable.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus::Surface {
void MidiMixerHandler::setControlsEnabled(bool enabled) {
  for (std::size_t index = 0; (*(state_.controlDescriptions + index))[0];
       ++index) {
    const auto &description = state_.controlDescriptions[index];
    if (description[37])
      state_.mappingTable->setControlEnabled(
          reinterpret_cast<const char *>(description.data()), enabled);
  }
}
} // namespace Presonus::Surface
