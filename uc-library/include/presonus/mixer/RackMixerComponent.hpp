#pragma once
#include "presonus/MuteGroupBase.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

namespace Presonus::Panel {
class ControlRegistrar;
}
namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
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

private:
  MixerComponentBase &base_;
  std::uint32_t &cascadeState_;
};
} // namespace Presonus::Mixer
