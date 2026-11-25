#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

#include "presonus/dsp/ControllerProperties.hpp"
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  unsigned old, input, dirty, rate;
  unsigned count = 0;
  while (fixture >> old >> input >> dirty >> rate) {
    ShelbyGEQController controller;
    Presonus::Dsp::SetupProperty property;
    property.rate = std::bit_cast<float>(input);
    controller.sourceState().processRateBits = old;
    controller.setupProcess(property);
    if (controller.sourceState().processDirty != dirty ||
        controller.sourceState().processRateBits != rate)
      return 1;
    ++count;
  }
  std::cout << count << " setupProcess cases\n";
  return count != 3;
}
