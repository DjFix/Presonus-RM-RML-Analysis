#include "presonus/surface/SurfaceOutputComponent.hpp"
namespace Presonus::Surface {
std::uint32_t SurfaceOutputComponent::levelAdjustable() {
  return channelMode == 2;
}
Core::Portable::Parameter *SurfaceOutputComponent::getDacValue() const {
  return getParameterByTag(400);
}
Core::Portable::Parameter *SurfaceOutputComponent::getLevel() const {
  return getParameterByTag(401);
}
} // namespace Presonus::Surface
