#include "presonus/uc/ClientRootComponent.hpp"
#include "core/system/coretime.h"

namespace Presonus::UC {

void *ClientRootComponent::castTo(int typeId) {
  if (typeId == kTypeID)
    return this;
  return ClientComponent::castTo(typeId);
}

ClientRootComponent *ClientRootComponent::getRoot() { return this; }

Core::abs_time ClientRootComponent::getSystemTime() const {
  // Match the native signed quotient at millisecond boundaries.
  constexpr Core::abs_time nanosecondsPerMillisecond = 1000000;
  return Core::SystemClock::getTime() / nanosecondsPerMillisecond;
}

} // namespace Presonus::UC
