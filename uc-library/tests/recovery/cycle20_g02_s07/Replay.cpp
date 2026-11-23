#include "presonus/MeterBallistics.hpp"

#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <string>

int main() {
  std::string role;
  while (std::cin >> role) {
    std::array<float, 6> input;
    for (float &point : input) {
      std::uint32_t bits;
      if (!(std::cin >> bits))
        return 1;
      point = std::bit_cast<float>(bits);
    }
    const Presonus::MeterBallistics::MeterDecayTable table(input.data());
    std::cout << role;
    for (const auto &entry : table.entries())
      std::cout << ' ' << std::bit_cast<std::uint32_t>(entry.amplitude) << ' '
                << std::bit_cast<std::uint32_t>(entry.normalizedInterval);
    std::cout << '\n';
  }
}
