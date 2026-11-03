#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>

namespace Presonus {
class DAWChannel;
class DAWChannelGroup;
class DAWDeviceFolder;
} // namespace Presonus
namespace presonus::surface {
// Independent source-port boundary. These operations do not establish the
// original DAW classes, interface vtable, ownership, or ARM object layout.
struct DAWMixerDependencies {
  virtual ~DAWMixerDependencies() = default;
  virtual Presonus::DAWChannel *focusChannel() = 0;
  virtual Presonus::DAWChannel *mainChannel() = 0;
  virtual int selectedMix() const = 0;
  virtual bool showStripMeters() const = 0;
  virtual Core::Portable::Component *
  component(Presonus::DAWChannel *) const = 0;
  virtual Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                            bool cue) const = 0;
  virtual int usedCount(Presonus::DAWDeviceFolder *) const = 0;
  virtual Core::Portable::Component *slot(Presonus::DAWDeviceFolder *,
                                          int) const = 0;
  virtual const char *channelType(Presonus::DAWChannel *) const = 0;
  virtual void connect(const char *, Core::Portable::Parameter *, const char *,
                       bool) = 0;
  virtual void assignChannels() = 0;
  virtual void assignControlLinkTargets() = 0;
  virtual void assignSelectedChannelTargets() = 0;
  virtual void assignFlexStrip() = 0;
};
struct DAWMixerState {
  bool clientPresent = false;
  Presonus::IMappingController *mappingController = nullptr;
  std::uint8_t shift = 0;
  std::uint8_t stripMeters = 0;
  bool channelNamesVisible = false;
  Presonus::DAWChannelGroup *mainGroup = nullptr;
  Presonus::DAWChannelGroup *inputGroup = nullptr;
  Presonus::DAWChannelGroup *outputGroup = nullptr;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Original encoded method identities with intentional portable storage and
// void return contracts. Unencoded original returns and layout remain pending.
class DAWMixerHandler {
public:
  struct MixTargets {
    Core::Portable::Parameter *level = nullptr;
    Core::Portable::Parameter *mute = nullptr;
    Core::Portable::Parameter *pan = nullptr;
    Core::Portable::Parameter *extraPan = nullptr;
  };
  DAWMixerHandler(presonus::surface::DAWMixerDependencies &dependencies,
                  presonus::surface::DAWMixerState &state,
                  Core::Portable::ParamList &automation)
      : dependencies(dependencies), state(state), automation(automation) {}
  bool shouldShowStripEncodersAsMeters() const;
  void updatePanEncoderConnection();
  void onChannelsChanged(DAWChannelGroup *);
  void getMixTargets(MixTargets &, DAWChannel *, int) const;
  void assignMainChannel();
  void onChannelParamChanged(DAWChannel *, Core::Portable::Parameter *);
  void onModifiersChanged();
  void onMappingParamChanged(Core::Portable::Parameter *);
  void onFocusChannelChanged();
  void onSlotCountChanged(DAWDeviceFolder *);
  void syncAutomationParams(DAWChannel *);

private:
  presonus::surface::DAWMixerDependencies &dependencies;
  presonus::surface::DAWMixerState &state;
  Core::Portable::ParamList &automation;
};
} // namespace Presonus::Surface
