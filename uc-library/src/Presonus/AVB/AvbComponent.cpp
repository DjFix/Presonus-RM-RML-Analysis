#include "presonus/avb/AvbComponent.hpp"
#include "core/system/coredebug.h"
#include <cstdio>
namespace Presonus::AVB {
void AvbComponent::addListener(ListenerType type, long long id, bool clock,
                               int mode, bool disable) {
  switch (type) {
  case Cascade:
    addCascadeListener(id, clock);
    break;
  case CSInput:
    addCSInputListener(id, clock);
    break;
  case ConsoleBus:
    addConsoleBusListener(id, clock, mode, disable);
    break;
  default:
    break;
  }
}
void AvbComponent::addCSInputListener(long long id, bool clock) {
  if (state_.csInput)
    services_.removeListener(state_.csInput);
  state_.csInput =
      services_.addListener(static_cast<unsigned long long>(id), 0, 4);
  Core::DebugPrintf("AvbComponent::addCSInputListener avb listener index = %d "
                    "clock to listener ? %d\n",
                    state_.csInput->index, clock);
  services_.configureStaticTalkerStreams();
}
void AvbComponent::addMixerInputListener(long long id, bool clock) {
  if (state_.mixer)
    services_.removeListener(state_.mixer);
  state_.mixer =
      services_.addListener(static_cast<unsigned long long>(id), 1, 32);
  std::printf("AvbComponent::addMixerInputListener avb listener index = %d "
              "clock to listener ? %d\n",
              state_.mixer->index, clock);
  if (clock)
    services_.setAudioClockToListener(state_.mixer);
}
void AvbComponent::addCascadeListener(long long id, bool clock) {
  if (state_.cascade)
    services_.removeListener(state_.cascade);
  state_.cascade =
      services_.addListener(static_cast<unsigned long long>(id), 0, 33);
  if (clock)
    services_.setAudioClockToListener(state_.cascade);
  std::printf("AvbComponent::addCascadeListener avb listener index = %d clock "
              "to listener ? %d\n",
              state_.cascade->index, clock);
  addMixerInputListener(id, false);
  if (state_.linkMode == 1)
    services_.routeLinkSlotsFromAvb();
  if (state_.mixer)
    services_.sendRoutingPacket(
        {{0x61736672, 24, state_.mixer->index, 0, 32, 0},
         state_.linkMode == 1});
}
void AvbComponent::addConsoleBusListener(long long id, bool clock, int mode,
                                         bool disable) {
  if (state_.console) {
    services_.removeListener(state_.console);
    state_.console = nullptr;
  }
  if (state_.mixer) {
    services_.removeListener(state_.mixer);
    state_.mixer = nullptr;
  }
  if (!disable) {
    state_.console =
        services_.addListener(static_cast<unsigned long long>(id), 0, 20);
    addMixerInputListener(id, clock);
  }
  const std::uint32_t index = state_.console ? state_.console->index : 0;
  services_.sendRoutingPacket(
      {{0x61646272, 28, 42, index, 0, state_.consoleSource},
       !disable && mode == 1});
  services_.sendRoutingPacket({{0x61646272, 28, 58, index, 18, 1}, !disable});
  services_.sendRoutingPacket({{0x61646272, 28, 60, index, 16, 2}, !disable});
}
} // namespace Presonus::AVB
