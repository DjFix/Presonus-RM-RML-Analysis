#include "presonus/frontier01/frontier01_w04.hpp"
#include "presonus/MackieControlModel.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus {
void MackieControlModel::sendHostConnectionConfirmation(bool accepted) {
  unsigned char message[14]{0xf0,
                            0,
                            0,
                            0x66,
                            hostConnectionIdentity[0],
                            static_cast<unsigned char>(accepted ? 3 : 4)};
  for (unsigned i = 1; i != 8; ++i)
    message[5 + i] = hostConnectionIdentity[i] & 0x7f;
  message[13] = 0xf7;
  sendMidiMessage(message, sizeof message);
}
FaderUnitComponent::~FaderUnitComponent() = default;
MackieControlExtender::~MackieControlExtender() = default;
MackieControlComponent::~MackieControlComponent() = default;
namespace Surface {
void MidiMixerHandler::setControlsEnabled(bool enabled) {
  for (std::size_t index = 0; (*(state_.controlDescriptions + index))[0];
       ++index) {
    const auto &description = state_.controlDescriptions[index];
    if (description[37])
      state_.mappingTable->setControlEnabled(
          reinterpret_cast<const char *>(description.data()), enabled);
  }
}
AudioUtilitiesPage::~AudioUtilitiesPage() = default;
StartPageComponent::~StartPageComponent() = default;
FaderUtilitiesPage::~FaderUtilitiesPage() = default;
} // namespace Surface
} // namespace Presonus
