#pragma once
#include "presonus/SLCascadeMeteringChannel.hpp"
namespace Presonus {
class SLRackFXBusComponent : public SLCascadeMeteringChannel {
public:
  SLRackFXBusComponent();
  ~SLRackFXBusComponent() override;
};
} // namespace Presonus
