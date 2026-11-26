#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLRackMonoMainComponent : public SLChannel {
public:
  SLRackMonoMainComponent();
  ~SLRackMonoMainComponent() override;
};
} // namespace Presonus
