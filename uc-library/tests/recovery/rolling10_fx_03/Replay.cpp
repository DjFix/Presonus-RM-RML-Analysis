#include "presonus/mixer/ReverbComponent.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
  Presonus::Mixer::ReverbComponent object(
      Presonus::Mixer::ReverbComponent::SourcePortConstruction{});
  auto *table = object.getSelectTypeMap();
  if (!table || object.getSelectTypeMap() != table)
    throw std::runtime_error("unstable table");
  for (int i = 0; i < 24; ++i) {
    std::uint32_t effect, value;
    std::memcpy(&effect, &table[i].effectType, 4);
    std::memcpy(&value, &table[i].value, 4);
    std::cout << table[i].family << ' ' << table[i].index << ' ' << effect
              << ' ' << value << ' ' << std::quoted(table[i].name) << '\n';
  }
}
