#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLRackStereoLineComponent : public SLChannel {
public:
  ~SLRackStereoLineComponent() override;
  void init(MixerClientComponentBase &, SLChannelBase &) override;
};
} // namespace Presonus
