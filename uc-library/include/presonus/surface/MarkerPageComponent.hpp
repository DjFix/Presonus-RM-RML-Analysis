#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus {
class DAWChannel;
class DAWChannelGroup;
class DAWDeviceFolder;
class IMappingController;
} // namespace Presonus
namespace Presonus::Surface {
// Intentional source-port state and inheritance. No original layout claim.
class MarkerPageComponent : public Core::Portable::Component {
public:
  struct TrackAccessor {
    const std::int32_t *markerCount{};
  };
  ~MarkerPageComponent();
  // Original callback return declaration remains pending; void is portable.
  virtual void onChannelsChanged(DAWChannelGroup *);
  virtual void onSlotCountChanged(DAWDeviceFolder *);
  // Observed native no-op callbacks; void is the portable declaration.
  virtual void onChannelParamChanged(DAWChannel *, Core::Portable::Parameter *);
  virtual void onFocusChannelChanged();
  virtual void setMappingController(IMappingController *);
  // Portable bool choice; original unencoded return declaration unresolved.
  bool isLocateMode() const;
  int getMaxMarkerListOffset(TrackAccessor &) const;
};
} // namespace Presonus::Surface
