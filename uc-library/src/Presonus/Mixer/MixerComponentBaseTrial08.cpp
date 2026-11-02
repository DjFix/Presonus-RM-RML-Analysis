#include "presonus/trial08/MixerComponentBase.hpp"
namespace Presonus::Mixer {
std::uint32_t MixerComponentBase::getSelectedChannel() const {
  return selectedChannel;
}
std::uint32_t MixerComponentBase::numClients() const { return clientCount; }
std::uint32_t MixerComponentBase::numHWMicLineIn() const {
  return hardwareMicLineInputs;
}
const char *MixerComponentBase::getCompanyName() const { return "presonus"; }
std::uint32_t MixerComponentBase::getSpectrumSendSlot() const {
  return hardwareMicLineInputs + std::uint32_t{12};
}
void MixerComponentBase::setTryingToQuit() { tryingToQuit = true; }
} // namespace Presonus::Mixer
