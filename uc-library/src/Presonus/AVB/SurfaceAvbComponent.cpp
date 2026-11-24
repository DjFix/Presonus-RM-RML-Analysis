#include "presonus/avb/SurfaceAvbComponent.hpp"
#include "presonus/dice/packet_services.hpp"
namespace Presonus::AVB {
// Compiler emits original D1/D2 variants. Actual pinned Component::~Component
// performs child/array/parameter cleanup; no original Core instructions
// execute.
SurfaceAvbComponent::~SurfaceAvbComponent() {}
} // namespace Presonus::AVB

namespace Presonus::AVB {
std::int64_t SurfaceAvbComponent::lastMaintenance_ = 0;

void SurfaceAvbComponent::handleTalkerStateChange(AvbTalker *) {}

void SurfaceAvbComponent::onIdle() {
  const std::int64_t now = presonus::dice::packetClockRawTicks() / 1000000;
  // Bounded source port: lastMaintenance_ + 500 must fit signed64, as
  // documented by the original split-word comparison domain. No base idle.
  if (now > lastMaintenance_ + 500)
    lastMaintenance_ = now;
}
} // namespace Presonus::AVB
