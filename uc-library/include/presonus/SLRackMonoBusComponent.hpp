#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLRackMonoBusComponent : public SLChannel {
public:
  SLRackMonoBusComponent();
  ~SLRackMonoBusComponent() override;
};
} // namespace Presonus
