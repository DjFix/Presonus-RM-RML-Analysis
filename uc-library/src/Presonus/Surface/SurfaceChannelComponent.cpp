#include "presonus/surface/SurfaceChannelComponent.hpp"
namespace Presonus::Surface {
SurfaceChannelComponent::SurfaceChannelComponent()
    : SurfaceChannelComponent(0) {}

SurfaceChannelComponent::SurfaceChannelComponent(int mode)
    : UC::ServerComponent(""), channelMode(static_cast<std::uint32_t>(mode)) {
  // Source-port names start empty. The original object's base +0x28 flag
  // has no established correspondence in the pinned CCL component.
}

SurfaceChannelComponent::~SurfaceChannelComponent() = default;
} // namespace Presonus::Surface
