#pragma once
#include "presonus/mixer/ChannelComponent.hpp"
#include <cstdint>
#include <stdexcept>
namespace Presonus::Mixer {
class MixerComponentBase;
}
namespace Presonus::Mixer {
// Partial real type relationship from native RTTI; intermediate native bases
// intentionally omitted. Construction/state are source-port-only, not
// recovered.
class TalkbackInputComponent : public ChannelComponent {
public:
  DECLARE_CORE_CLASS(0x1742e4, TalkbackInputComponent, ChannelComponent)
  using ChannelComponent::ChannelComponent;
  // Independent borrowed source-port state, never an ARM object layout.
  // The state, mixer and mixer.sceneSettings tree must outlive all calls and
  // observer registration. Keep registration/removal paired before teardown.
  struct SourcePortState {
    MixerComponentBase *mixer = nullptr;
    std::uint8_t postFader = 1;
  };
  void bindTalkbackState(SourcePortState &state) {
    if (talkbackState_ && talkbackState_ != &state)
      throw std::logic_error("Talkback state already bound");
    talkbackState_ = &state;
  }
  // uint8_t and void are source-port return choices. Original return types
  // are not encoded by mangling. Raw byte behavior is preserved, including
  // values outside constructor-reachable bool state.
  std::uint8_t isPostFaderAux(int);
  void addRemoveObservers(bool);

private:
  SourcePortState *talkbackState_ = nullptr;
  SourcePortState &talkbackState() const {
    if (!talkbackState_)
      throw std::logic_error("Talkback state is unbound");
    return *talkbackState_;
  }
};
} // namespace Presonus::Mixer
