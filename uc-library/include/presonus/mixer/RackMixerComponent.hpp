#pragma once
#include "presonus/MuteGroupBase.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cstdint>
#include <vector>

namespace Presonus::NOAA {
class TCardHandler;
}
namespace Presonus::Panel {
class ControlRegistrar;
}
namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
class TalkbackInputComponent;
class FXComponent;
class RackMixerComponent {
public:
  RackMixerComponent(MixerComponentBase &base, std::uint32_t &cascadeState)
      : base_(base), cascadeState_(cascadeState) {}
  void onCascadeStateChange();
  void lineSenseChanged(const Presonus::Panel::ControlRegistrar &,
                        int lineIndex, int senseValue);
  // Source-port bindings: reuse base_.sceneChannels, channelIdentity and each
  // channel's authoritative portableState().mute. Borrow the same MixerData
  // consumed by MuteGroupBase; no shadow channel/mute collection.
  presonus::mute_group_port::MixerData *muteGroups = nullptr;
  // Native +0x174 supplies a signed loop bound. Independent portable state,
  // not an original field/layout or hardware-model declaration.
  std::int32_t auxiliaryRouteCount = 0;
  // void returns are provisional source-port declarations (pending).
  void setupAllMutesGroup();
  void buildAuxRouteList(Core::Portable::ListParam &);
  // Independent state relocation for native Talkback +0x234/+0x22c.
  // Entries borrow real typed identities; the application owns this storage.
  struct TalkbackRouteState {
    TalkbackInputComponent *identity{};
    std::uint32_t route{}, mode{};
  };
  std::vector<TalkbackRouteState> talkbackRoutes;
  void getTDMRoutes(int, unsigned char &, unsigned char &, unsigned int &);
  // Borrow authoritative collections for native count/scan observations;
  // these are source-port views, not duplicate arrays or original fields.
  const Core::Vector<ChannelComponent *> *danteSourceChannels{};
  const Core::Vector<FXComponent *> *danteEffects{};
  const Core::Vector<ChannelComponent *> *digitalInputCandidates{};
  Presonus::NOAA::TCardHandler *danteHandler{};
  void setDanteStaticRoutes();

private:
  MixerComponentBase &base_;
  std::uint32_t &cascadeState_;
};
} // namespace Presonus::Mixer
