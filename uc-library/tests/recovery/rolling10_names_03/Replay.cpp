#include "presonus/surface/ControlName.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
int main() {
  unsigned count = 0;
  for (auto input : {std::string(), std::string("gain"), std::string(31, 'x'),
                     std::string(32, 'x'), std::string(80, 'x')}) {
    for (int index : {-2, -1, 0, 9, 2147483647}) {
      std::uint32_t bits = static_cast<std::uint32_t>(index) + 1u;
      int number;
      std::memcpy(&number, &bits, 4);
      Core::CString32 provider;
      provider.appendFormat("%s_%02d", input.c_str(), number);
      Presonus::Surface::ControlName actual(input.c_str(), index);
      assert(std::strcmp(actual.str(), provider.str()) == 0);
      ++count;
    }
  }
  std::cout << count << " provider comparisons passed\n";
}
