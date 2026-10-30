#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
int main() {
  using namespace presonus::lpc;
  std::uint32_t part, size, start, fill, expected;
  std::array<std::uint32_t, 8> values;
  unsigned count = 0;
  while (std::cin >> part >> size >> start >> fill >> expected) {
    for (auto &value : values)
      std::cin >> value;
    assert(std::cin && fill <= 255);
    const std::uint32_t pattern = fill * 0x01010101u;
    ImageGeometryState initial{size,    part,    start,   pattern,
                               pattern, pattern, pattern, pattern};
    Presonus::LPCProgrammer programmer(ImageStateOnly{}, initial);
    const int result = programmer.initAddresses();
    const auto &state = ImageGeometryAccess::state(programmer);
    std::array<std::uint32_t, 8> actual = {
        state.raw08, state.raw18, state.raw30, state.raw34,
        state.raw38, state.raw40, state.raw48, state.raw4c};
    assert(static_cast<unsigned>(result) == expected && actual == values);
    std::cout << "STATE " << result;
    for (auto value : actual)
      std::cout << ' ' << value;
    std::cout << '\n';
    ++count;
  }
  assert(count == 20700);
  std::cerr << "PASS original_image_geometry_cases=" << count << '\n';
}
