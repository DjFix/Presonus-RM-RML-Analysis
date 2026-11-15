#include "presonus/mixer/GambitMixerComponent.hpp"
#include <iostream>
int main() {
  unsigned input;
  while (std::cin >> input) {
    const Presonus::Mixer::GambitMixerComponent object(
        Presonus::Mixer::GambitMixerComponent::SourcePortConstruction{});
    std::cout << object.numHWMicLineIn() << '\n';
  }
}
