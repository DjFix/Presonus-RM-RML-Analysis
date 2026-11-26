#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLCascadeMeteringChannel : public SLChannel {
public:
  SLCascadeMeteringChannel();
  ~SLCascadeMeteringChannel() override;
  void slaveMixerChanged();
  void updateAggregateMeter(int, float);
  void updateSlaveChannelLevel(float);
  // Independent source-port inspection; no original accessor/ABI credit.
  float sourcePortLocalChannelLevel() const noexcept { return localLevel_; }
  float sourcePortSlaveChannelLevel() const noexcept { return slaveLevel_; }
  // Explicit borrowed peer projection; not original ownership/layout.
  void bindSourcePortMasterChannel(SLCascadeMeteringChannel *master) {
    masterChannel_ = master;
  }

private:
  SLCascadeMeteringChannel *masterChannel_ = nullptr;
  // Independent initialized fallbacks. Native ctor sets only the peer pointer;
  // original level words require later initialization before observation.
  float localLevel_ = 0.f;
  float slaveLevel_ = 0.f;
};
} // namespace Presonus
