#include "presonus/SLCascadeMeteringChannel.hpp"
namespace Presonus {
SLCascadeMeteringChannel::SLCascadeMeteringChannel() = default;
SLCascadeMeteringChannel::~SLCascadeMeteringChannel() = default;
void SLCascadeMeteringChannel::slaveMixerChanged() { slaveLevel_ = 0.f; }
void SLCascadeMeteringChannel::updateSlaveChannelLevel(float level) {
  slaveLevel_ = level;
}
void SLCascadeMeteringChannel::updateAggregateMeter(int kind, float level) {
  if (masterChannel_) {
    if (kind == 1818588780)
      masterChannel_->updateSlaveChannelLevel(level);
    return;
  }
  localLevel_ = level;
  SLChannelBase::updateMeter(kind, localLevel_ + slaveLevel_);
}
} // namespace Presonus
