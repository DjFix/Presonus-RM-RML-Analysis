#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"

namespace Presonus {
namespace {
// Actual application table fields from both version-bound ELF ParamList ranges.
// Genuine CCL ParamInfo preserves inline names; host optional metadata pointer
// widths differ. These are source-based metadata bindings, not ARM layout
// copies.
constexpr Core::Portable::ParamInfo channelParameters[] = {
    PARAM_TOGGLE(15000, "on_left", 0, nullptr, 0),
    PARAM_TOGGLE(15001, "paste_select", 0, nullptr, 0),
    PARAM_INT(15002, "color_index", 0, 16, 16, nullptr, nullptr, 0,
              PARAM_PRIVATE)};
Core::Portable::NumericParam *numeric(SLChannelBase &channel, int tag) {
  return Core::Portable::NumericParam::cast(channel.getParameterByTag(tag));
}
} // namespace
void SLChannelBase::init(MixerClientComponentBase &mixer, SLChannelBase &peer) {
  mixer_ = &mixer;
  bindSourcePortMixer(&mixer);
  addParameters(channelParameters, 3);
  if (auto *index = numeric(*this, 15002)) {
    bindWritableColorIndexParameter(*index);
    index->setFeedbackNeeded(true);
  }
  levelMeter_.configureSourcePortDecayRate(0.015f);
  for (auto &meter : gainReduction_)
    meter.configureSourcePortDecayRate(0.025f);
  if (auto *left = getParameterByTag(15000))
    left->setValue((getNumber() & 1) ? 1.f : 0.f, true);
  linker_ = new ParamLinker(mixer, *this, peer);
  idleTimer_.beginAction(-1.f);
}
void SLChannel::init(MixerClientComponentBase &mixer, SLChannelBase &peer) {
  SLChannelBase::init(mixer, peer);
  selection_ = getParameterByTag(13);
  selection_->setPublic(false);
  linkedSelection_ = this == &peer ? nullptr : peer.getParameterByTag(13);
  color_ = Core::Portable::ColorParam::cast(getParameterByTag(3));
  sourcePortLevelMeter().bindParameters(numeric(*this, 5), numeric(*this, 6));
  sourcePortGainReductionMeter(0).bindParameters(numeric(*this, 9), nullptr);
  sourcePortGainReductionMeter(1).bindParameters(numeric(*this, 11), nullptr);
  sourcePortGainReductionMeter(2).bindParameters(numeric(*this, 10), nullptr);
  sourcePortGainReductionMeter(3).bindParameters(numeric(*this, 12), nullptr);
  for (int tag : {411, 21, 22})
    if (auto *parameter = getParameterByTag(tag))
      parameter->setFeedbackNeeded(true);
  if (color_) {
    color_->setFeedbackNeeded(true);
    color_->changed();
  }
}
} // namespace Presonus
