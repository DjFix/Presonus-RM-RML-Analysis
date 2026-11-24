#include "presonus/mixer/GambitMixerComponent.hpp"

#include <array>
#include <cstring>
#include <iostream>

int main() {
  using Presonus::Mixer::GambitMixerComponent;
  unsigned seed;
  while (std::cin >> seed) {
    struct {
      std::uint32_t before;
      GambitMixerComponent mixer;
      std::uint32_t after;
    } state{
        seed,
        GambitMixerComponent(GambitMixerComponent::SourcePortConstruction{}),
        ~seed};
    std::array<unsigned char, sizeof(state.mixer)> image{};
    std::memcpy(image.data(), &state.mixer, image.size());
    const auto result = state.mixer.getDanteTalkbackSlot();
    const bool receiverUnchanged =
        std::memcmp(image.data(), &state.mixer, image.size()) == 0;
    const bool canariesUnchanged = state.before == seed && state.after == ~seed;
    std::cout << result << ' ' << receiverUnchanged << ' ' << canariesUnchanged
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
