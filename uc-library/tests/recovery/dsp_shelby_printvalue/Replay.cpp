#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

#include "presonus/dsp/ControllerInfo.hpp"
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  unsigned value;
  int index, capacity;
  unsigned count = 0;
  while (fixture >> value >> index >> capacity) {
    std::array<char, 24> bytes;
    bytes.fill(static_cast<char>(0xa5));
    Presonus::StringResult output{bytes.data(), capacity};
    ShelbyGEQController controller;
    controller.printValue(output, index, std::bit_cast<float>(value));
    for (unsigned char observed : bytes) {
      unsigned expected;
      if (!(fixture >> expected) || observed != expected)
        return 1;
    }
    ++count;
  }
  std::cout << count << " printValue cases\n";
  return count != 6;
}
