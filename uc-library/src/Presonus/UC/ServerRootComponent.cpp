#include "presonus/uc/ServerRootComponent.hpp"

#include "core/system/coretime.h"

namespace Presonus::UC {

void *ServerRootComponent::castTo(int typeId) {
  // The firmware accepts these primary-receiver IDs from its class tables.
  switch (typeId) {
  case kTypeID:
  case 0x5376436f:
  case 0x436f6d70:
    return this;
  default:
    return nullptr;
  }
}

ServerRootComponent *ServerRootComponent::getRoot() { return this; }

Core::abs_time ServerRootComponent::getSystemTime() const {
  // The original application divides the signed nanosecond clock directly.
  return Core::SystemClock::getTime() / 1000000;
}

} // namespace Presonus::UC
