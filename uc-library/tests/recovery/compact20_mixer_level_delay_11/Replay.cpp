#include "presonus/mixer/DelayComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
int main() {
  Presonus::Mixer::DelayComponent component(
      Presonus::Mixer::DelayComponent::SourcePortConstruction{});
  const auto *table = component.getSelectTypeMap();
  std::cout << "stable " << (table == component.getSelectTypeMap()) << '\n';
  for (int i = 0; i < 21; ++i) {
    std::uint32_t effect, value;
    std::memcpy(&effect, &table[i].effectType, sizeof(effect));
    std::memcpy(&value, &table[i].value, sizeof(value));
    std::cout << table[i].family << ' ' << table[i].index << ' ' << effect
              << ' ' << value << ' ' << std::quoted(table[i].name) << '\n';
  }
}
