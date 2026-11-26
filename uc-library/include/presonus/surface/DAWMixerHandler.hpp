#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

namespace Presonus {
class DAWChannel;
class DAWChannelGroup;
class DAWDeviceFolder;
class DAWClientComponent;
class MappingTable;
} // namespace Presonus
namespace Presonus::Surface {
class DawFxPageComponent;
}
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
  // Borrowed typed source-port assembly, not original client storage/layout.
  Presonus::DAWClientComponent *client = nullptr;
  Presonus::MappingTable *mappingTable = nullptr;
  Presonus::IMappingController *mappingController = nullptr;
  std::uint8_t shift = 0;
  std::uint8_t stripMeters = 0;
  bool channelNamesVisible = false;
  Presonus::DAWChannelGroup *mainGroup = nullptr;
  Presonus::DAWChannelGroup *inputGroup = nullptr;
  Presonus::DAWChannelGroup *outputGroup = nullptr;
  // Portable word observed through the borrowed client; only bit zero is used.
  std::uint32_t clientActivationFlags = 0;
  // Stable ordered roster of borrowed DAW pages. Pages must outlive use of
  // the roster and the roster must stay unchanged during controller routing.
  std::vector<std::reference_wrapper<Presonus::Surface::DawFxPageComponent>>
      dawPages;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Original encoded method identities with intentional storage and
// portable return contracts. Unencoded original returns and layout remain
// pending.
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
  // The two-argument portable constructor owns its automation list. The
  // three-argument constructor continues to use the caller's list.
  DAWMixerHandler(presonus::surface::DAWMixerDependencies &dependencies,
                  presonus::surface::DAWMixerState &state);
  virtual ~DAWMixerHandler();

  DAWMixerHandler(const DAWMixerHandler &) = delete;
  DAWMixerHandler &operator=(const DAWMixerHandler &) = delete;

  Core::Portable::ParamList &automationParameters() { return automation; }

  // Portable int return spellings; original return declarations remain pending.
  int getSelectedMix() const;
  int getSelectedMeterMode() const;
  bool canActivate() const;
  const char *getName() const;
  bool shouldShowStripEncodersAsMeters() const;
  void setController(Presonus::IMappingController *controller);
  void updatePanEncoderConnection();
  void onChannelsChanged(DAWChannelGroup *);
  void getMixTargets(MixTargets &, DAWChannel *, int) const;
  void assignMainChannel();
  void onChannelParamChanged(DAWChannel *, Core::Portable::Parameter *);
  void onModifiersChanged();
  bool handleMappingRadioGroup(Core::Portable::Parameter *);
  void onMappingParamChanged(Core::Portable::Parameter *);
  void onFocusChannelChanged();
  void onSlotCountChanged(DAWDeviceFolder *);
  void syncAutomationParams(DAWChannel *);
  DAWChannel *getMainChannel();
  void assignControlLinkTargets();
  void assignSelectedChannelTargets();
  void assignStripTargets(DAWChannelGroup *, int, const char *);
  void assignChannels();

private:
  presonus::surface::DAWMixerDependencies &dependencies;
  presonus::surface::DAWMixerState &state;
  std::optional<Core::Portable::ParamList> ownedAutomation;
  Core::Portable::ParamList &automation;
};
} // namespace Presonus::Surface
