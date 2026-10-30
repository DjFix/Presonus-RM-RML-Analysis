#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cassert>
#include <iostream>
int main() {
  Presonus::LPCProgrammer instance(presonus::lpc::GeometryOnly{});
  unsigned part, expected;
  unsigned count = 0;
  while (std::cin >> part >> expected) {
    assert(instance.getLastSector(part) == expected);
    ++count;
  }
  assert(count != 0);
  std::cerr << "PASS original_geometry_cases=" << count << '\n';
}
