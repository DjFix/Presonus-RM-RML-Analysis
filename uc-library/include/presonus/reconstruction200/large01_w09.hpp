#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus::Surface {
// Intentional source-port state and inheritance. No original layout claim.
class MarkerPageComponent : public Core::Portable::Component {
public:
  struct TrackAccessor {
    const std::int32_t *markerCount{};
  };
  ~MarkerPageComponent();
  int getMaxMarkerListOffset(TrackAccessor &) const;
};
class DAWDialogHandler : public Core::Portable::Component {
public:
  ~DAWDialogHandler();
};
} // namespace Presonus::Surface
