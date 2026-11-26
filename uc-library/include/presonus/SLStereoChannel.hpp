#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
// Natural source-port embedded ownership; no standalone original C1/C2 claim.
class SLStereoChannel : public SLChannel {
public:
  SLStereoChannel() = default;
  ~SLStereoChannel() override;
  void init(MixerClientComponentBase &, SLChannelBase &) override;
  void idleMeters() override;
  void updateStereoMeters(int, float, float);
  MeterMaid &sourcePortRightMeter() { return rightMeter_; }

private:
  MeterMaid rightMeter_;
};
} // namespace Presonus
