#include "presonus/mixer/DelayComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
int main() {
  Presonus::Mixer::DelayComponent component(
      Presonus::Mixer::DelayComponent::SourcePortConstruction{});
  std::uint64_t input;
  while (std::cin >> input) {
    const auto bits = static_cast<std::uint32_t>(input);
    std::int32_t value;
    std::memcpy(&value, &bits, sizeof(value));
    const auto result = component.getEffectTypeInternal(
        static_cast<Presonus::EffectType>(value));
    std::cout << static_cast<std::uint32_t>(result) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
