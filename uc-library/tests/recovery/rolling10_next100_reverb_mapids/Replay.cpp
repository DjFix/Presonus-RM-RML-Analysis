#include "presonus/mixer/ReverbComponent.hpp"
#include <cstdint>
#include <iostream>
int main() {
  Presonus::Mixer::ReverbComponent first(
      Presonus::Mixer::ReverbComponent::SourcePortConstruction{});
  Presonus::Mixer::ReverbComponent second(
      Presonus::Mixer::ReverbComponent::SourcePortConstruction{});
  int receiver;
  std::int64_t value;
  while (std::cin >> receiver >> value) {
    auto &object = receiver ? second : first;
    std::cout << object.mapIDs(static_cast<int>(value)) << '\n';
  }
}
