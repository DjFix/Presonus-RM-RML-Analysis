#include "presonus/surface/MarkerPageComponent.hpp"
#include <bit>
namespace Presonus::Surface {
MarkerPageComponent::~MarkerPageComponent() = default;
int MarkerPageComponent::getMaxMarkerListOffset(TrackAccessor &track) const {
  if (!track.markerCount)
    return 0;
  auto count =
      std::bit_cast<std::int32_t>(std::uint32_t(*track.markerCount) - 1u);
  auto result = (count / 5) * 5;
  return result < 0 ? 0 : result;
}
} // namespace Presonus::Surface
