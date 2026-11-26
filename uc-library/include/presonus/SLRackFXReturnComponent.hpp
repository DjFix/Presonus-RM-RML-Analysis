#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLRackFXReturnComponent : public SLChannel {
public:
  SLRackFXReturnComponent();
  ~SLRackFXReturnComponent() override;
};
} // namespace Presonus
