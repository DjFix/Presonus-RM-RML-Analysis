#include "presonus/SLStereoChannel.hpp"
namespace Presonus {
SLStereoChannel::~SLStereoChannel() = default;
void SLStereoChannel::init(MixerClientComponentBase &mixer,
                           SLChannelBase &peer) {
  SLChannel::init(mixer, peer);
  rightMeter_.bindParameters(
      Core::Portable::NumericParam::cast(getParameterByTag(7)),
      Core::Portable::NumericParam::cast(getParameterByTag(8)));
  rightMeter_.configureSourcePortDecayRate(0.025f);
}
void SLStereoChannel::idleMeters() {
  SLChannelBase::idleMeters();
  rightMeter_.idle();
}
void SLStereoChannel::updateStereoMeters(int kind, float left, float right) {
  SLChannelBase::updateMeter(kind, left);
  if (kind == 1818588780)
    rightMeter_.setLevel(right);
}
} // namespace Presonus
