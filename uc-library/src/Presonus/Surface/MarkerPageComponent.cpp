#include "presonus/surface/MarkerPageComponent.hpp"
#include <bit>
namespace Presonus::Surface {
MarkerPageComponent::~MarkerPageComponent() = default;
void MarkerPageComponent::onChannelsChanged(DAWChannelGroup *) {}
void MarkerPageComponent::onSlotCountChanged(DAWDeviceFolder *) {}
void MarkerPageComponent::onChannelParamChanged(DAWChannel *,
                                                Core::Portable::Parameter *) {}
void MarkerPageComponent::onFocusChannelChanged() {}
void MarkerPageComponent::setMappingController(IMappingController *) {}
bool MarkerPageComponent::isLocateMode() const {
  auto *parameter = getParameterByTag(1007);
  return parameter && parameter->getValue() > 0.f;
}
int MarkerPageComponent::getMaxMarkerListOffset(TrackAccessor &track) const {
  if (!track.markerCount)
    return 0;
  auto count =
      std::bit_cast<std::int32_t>(std::uint32_t(*track.markerCount) - 1u);
  auto result = (count / 5) * 5;
  return result < 0 ? 0 : result;
}
} // namespace Presonus::Surface
