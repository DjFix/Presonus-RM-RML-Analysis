#include "presonus/DAWTimeInfo.hpp"
#include <array>
#include <fstream>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  if (!fixture)
    return 3;
  unsigned int pattern, value, expected;
  unsigned int count = 0;
  while (fixture >> pattern >> value >> expected) {
    std::array<std::uint8_t, 512> state{};
    for (unsigned int i = 0; i < state.size(); ++i)
      state[i] = static_cast<std::uint8_t>(i * 37 + pattern * 71);
    state[0x134] = static_cast<std::uint8_t>(value);
    const auto before = state;
    const Presonus::DAWTimeInfo info(state.data());
    if (info.isMusicalDisplay() != expected || state != before)
      return 4;
    ++count;
  }
  if (!fixture.eof() || count != 1024)
    return 5;
  std::cout
      << "DAWTimeInfo native differential cases: " << count
      << "; all byte values, four surrounding patterns; no state writes\n";
}
