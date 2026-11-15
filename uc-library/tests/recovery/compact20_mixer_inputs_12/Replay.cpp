#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <cstdint>
#include <iostream>
int main() {
  using Talkback = Presonus::Mixer::TalkbackInputComponent;
  Talkback component(
      Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
  Talkback::SourcePortState state;
  component.bindTalkbackState(state);
  unsigned value;
  std::uint32_t argument;
  while (std::cin >> value >> argument) {
    state.postFader = static_cast<std::uint8_t>(value);
    std::cout << static_cast<unsigned>(
                     component.isPostFaderAux(static_cast<int>(argument)))
              << '\n';
  }
}
