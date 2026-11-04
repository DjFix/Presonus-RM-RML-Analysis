#include "presonus/surface/SurfaceOutputComponent.hpp"
namespace Presonus::Surface {
std::uint32_t SurfaceOutputComponent::levelAdjustable() {
  return channelMode == 2;
}
} // namespace Presonus::Surface
