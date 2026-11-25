#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  int index;
  unsigned old, value, stored, dirty, marker;
  unsigned count = 0;
  while (fixture >> index >> old >> value >> stored >> dirty >> marker) {
    ShelbyGEQController controller;
    controller.portableMarkers().fill(0x35);
    auto &values = controller.portableValues();
    if (index < 33)
      values[index] = std::bit_cast<float>(old);
    controller.setValue(index, std::bit_cast<float>(value));
    if (controller.sourceState().processDirty != dirty ||
        (index < 33 && std::bit_cast<unsigned>(values[index]) != stored))
      return 1;
    for (auto observed : controller.portableMarkers())
      if (observed != marker)
        return 1;
    ++count;
  }
  std::cout << count << " setValue cases\n";
  return count != 7;
}
