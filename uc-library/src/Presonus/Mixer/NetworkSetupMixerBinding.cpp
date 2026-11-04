#include "presonus/mixer/NetworkSetupComponent.hpp"
namespace Presonus::Mixer {
void NetworkSetupComponent::setMixerHandler(AVBRemoteMixerHandler *handler) {
  state_.mixerHandler = handler;
  state_.hasRemoteHandler = handler != nullptr;
}
} // namespace Presonus::Mixer
