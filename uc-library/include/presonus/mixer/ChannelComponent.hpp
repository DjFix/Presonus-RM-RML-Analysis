#pragma once

#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include <array>
#include <cstdint>
#include <stdexcept>

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
// Real CCL/type hierarchy for the partial source port; intermediate native
// bases are intentionally omitted, with original RTTI retained in evidence.
class ChannelComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x173594, ChannelComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit ChannelComponent(SourcePortConstruction) {}
  ChannelComponent(SourcePortConstruction, presonus::mixer::ChannelState &state)
      : state_(&state) {}
  ChannelComponent(presonus::mixer::ChannelState &state,
                   presonus::mixer::ChannelApplicationServices &services)
      : state_(&state), services_(&services) {}
  // Complete a partial source-port binding once; never silently replace an
  // existing authoritative state used by other methods.
  void bindSourcePortState(presonus::mixer::ChannelState &state) {
    if (state_ && state_ != &state)
      throw std::logic_error("ChannelComponent state already bound");
    state_ = &state;
  }
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
  presonus::mixer::ChannelState &portableState() const { return state(); }

private:
  // Partial typed construction does not fabricate app state or services.
  // Unbound app operations fail before dereferencing missing providers.
  presonus::mixer::ChannelState *state_ = nullptr;
  presonus::mixer::ChannelState &state() const {
    if (!state_)
      throw std::logic_error("ChannelComponent state is unbound");
    return *state_;
  }
  presonus::mixer::ChannelApplicationServices *services_ = nullptr;
  presonus::mixer::ChannelApplicationServices &services() const {
    if (!services_)
      throw std::logic_error("ChannelComponent services are unbound");
    return *services_;
  }
};
} // namespace Presonus::Mixer
