#include "presonus/surface/FxPresetsPageComponent.hpp"
#include <cstring>
namespace Presonus::Surface {
FxPresetsPageComponent::~FxPresetsPageComponent() = default;
Core::CStringBuffer<256> &
FxPresetsPageComponent::getTargetUrl(Core::CStringBuffer<256> &out) {
  const std::uint32_t bits = static_cast<std::uint32_t>(channelIndex_) + 1u;
  std::int32_t channel;
  std::memcpy(&channel, &bits, sizeof channel);
  return out.appendFormat("fx/ch%d", channel);
}
} // namespace Presonus::Surface
