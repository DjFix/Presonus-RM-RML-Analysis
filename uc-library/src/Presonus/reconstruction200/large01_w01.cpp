#include "presonus/reconstruction200/large01_w01.hpp"
#include "presonus/avb/AvbComponent.hpp"
#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include <cstring>

namespace Presonus::AVB {
int AvbComponent::getConsoleTalkbackListenerAndChannel(int *listener,
                                                       int *channel) {
  if (state_.console) {
    *channel = 19;
    *listener = state_.console->index;
  }
  return 0;
}
int AvbComponent::getCSTalkbackListenerAndChannel(int *listener, int *channel) {
  if (state_.csInput) {
    *channel = 0;
    *listener = state_.csInput->index;
  }
  return 0;
}
int AvbComponent::getListenerAndChannelForInput(int *listener, int *channel,
                                                int input, bool cs) {
  *listener = 0;
  *channel = input;
  if (state_.mixer)
    *listener = state_.mixer->index;
  if (cs && state_.csInput && input > 29) {
    *listener = state_.csInput->index;
    *channel = input - 30;
  }
  return 0;
}
int AvbComponent::getTalkerAndChannelForInput(int *talker, int *channel,
                                              int input) {
  // ARM ADD wraps modulo 2^32, including outside the normal audio domain.
  auto bits = static_cast<std::uint32_t>(input) + 33u;
  int result;
  static_assert(sizeof(result) == sizeof(bits));
  std::memcpy(&result, &bits, sizeof(result));
  *talker = 0;
  *channel = result;
  return 0;
}
bool AvbComponent::hasListeners() const {
  return state_.cascade || state_.mixer || state_.csInput || state_.console;
}
int AvbComponent::getAVBListenerIndex(int index) const {
  if (static_cast<unsigned>(index) > 3u)
    return -1;
  const presonus::avb::Listener *slots[] = {state_.cascade, state_.mixer,
                                            state_.csInput, state_.console};
  return slots[index] ? slots[index]->index : -1;
}
// Compiler emits original D1/D2 variants. Actual pinned Component::~Component
// performs child/array/parameter cleanup; no original Core instructions
// execute.
SurfaceAvbComponent::~SurfaceAvbComponent() {}
} // namespace Presonus::AVB
namespace Presonus::Mixer {
void NetworkSetupComponent::setMixerHandler(AVBRemoteMixerHandler *handler) {
  state_.mixerHandler = handler;
  state_.hasRemoteHandler = handler != nullptr;
}
} // namespace Presonus::Mixer
namespace Presonus::Surface {
bool NetworkSetupComponent::isSlaveItem(const UC::NetworkItem *item) const {
  if (state_.dependencies.kind(*item) != 0)
    return false;
  for (int i = 0; i < state_.mixers.count(); ++i)
    if (state_.dependencies.associatedItem(*state_.mixers[i]) == item)
      return true;
  return false;
}
} // namespace Presonus::Surface
