#include "presonus/SLRackStereoLineComponent.hpp"
namespace Presonus {
SLRackStereoLineComponent::~SLRackStereoLineComponent() = default;
void SLRackStereoLineComponent::init(MixerClientComponentBase &mixer,
                                     SLChannelBase &peer) {
  SLChannel::init(mixer, peer);
  releaseSourcePortLinker();
}
} // namespace Presonus
