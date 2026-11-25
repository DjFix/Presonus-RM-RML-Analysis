#pragma once

#include "core/public/coretypes.h"
#include "presonus/uc/ServerComponent.hpp"

namespace Presonus::UC {

// Portable primary-component subset. Native secondary bases and lifecycle are
// outside this interface.
class ServerRootComponent : public ServerComponent {
public:
  using ServerComponent::ServerComponent;
  DECLARE_CORE_CLASS_(0x53765274, ServerRootComponent)
  void *castTo(int typeId) override;
  ServerRootComponent *getRoot();
  Core::abs_time getSystemTime() const;
};

} // namespace Presonus::UC
