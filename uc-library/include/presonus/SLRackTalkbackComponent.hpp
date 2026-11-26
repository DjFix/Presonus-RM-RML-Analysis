#pragma once
#include "presonus/SLChannel.hpp"
namespace Presonus {
class SLRackTalkbackComponent : public SLChannel {
public:
  SLRackTalkbackComponent();
  ~SLRackTalkbackComponent() override;
};
} // namespace Presonus
