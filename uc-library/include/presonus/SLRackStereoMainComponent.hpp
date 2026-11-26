#pragma once
#include "presonus/SLStereoChannel.hpp"
namespace Presonus {
class SLRackStereoMainComponent : public SLStereoChannel {
public:
  SLRackStereoMainComponent();
  ~SLRackStereoMainComponent() override;
};
} // namespace Presonus
