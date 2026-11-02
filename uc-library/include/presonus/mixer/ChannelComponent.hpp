#pragma once

#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include <array>
#include <cstdint>

namespace Presonus::Mixer {
class ChannelComponent;
}

namespace presonus::mixer {
// Independent portable binding state. These are not original ARM object fields.
struct ChannelEnvironment {
  Core::Portable::Component *globalParameters{};
  Core::Portable::Component *soloParameters{};
  Core::Portable::Parameter *panModeCache{};
  bool soloBlockedA{}, soloBlockedB{};
  float panLaw{};
};
struct ChannelState {
  Core::Portable::Parameter *mute{}, *pan{}, *linkedPan{}, *level{}, *solo{};
  Core::Portable::Parameter *locateIndicator{}, *locatePosition{};
  Core::Portable::Parameter *mainAssign{}, *monoAssign{}, *soloModeCache{};
  Core::Portable::StringParam *name{};
  Core::Portable::Component *children{};
  ChannelEnvironment *environment{};
  std::array<float, 3> coefficients{};
  std::array<float, 2> soloCoefficients{};
  float gain{}, lastLocate{};
  unsigned linkSide{};
  bool active{};
  std::array<std::uint32_t, 8> updates{};
};
// App-specific dependencies stay explicit; this interface is not recovered ABI.
class ChannelApplicationServices {
public:
  virtual ~ChannelApplicationServices() = default;
  virtual bool isLinked(const Presonus::Mixer::ChannelComponent &) const = 0;
  virtual void removeLink(Presonus::Mixer::ChannelComponent &) = 0;
  virtual Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) = 0;
  virtual void faderLocateDirty(Presonus::Mixer::ChannelComponent &) = 0;
  virtual void coefficientsChanged(Presonus::Mixer::ChannelComponent &,
                                   bool solo) = 0;
};
} // namespace presonus::mixer

namespace Presonus::Mixer {
// Source port only: original inheritance, layout and return declarations
// pending.
class ChannelComponent {
public:
  ChannelComponent(presonus::mixer::ChannelState &state,
                   presonus::mixer::ChannelApplicationServices &services)
      : state_(state), services_(services) {}
  virtual ~ChannelComponent() = default;
  void postDoUpdates();
  bool isLCRPanMode() const;
  void removeLink();
  virtual void levelUpdate();
  void linkChannelName();
  void doUpdates();
  virtual void soloCoeffUpdate();
  void checkFaderLocateSync();
  void resetEQDyn();
  bool handleFaderLocate(float value) const;
  presonus::mixer::ChannelState &portableState() const { return state_; }

private:
  presonus::mixer::ChannelState &state_;
  presonus::mixer::ChannelApplicationServices &services_;
};
} // namespace Presonus::Mixer
