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
  int channel, baseId;
  if (!(fixture >> channel >> baseId))
    return 2;
  struct Derived final : ShelbyGEQController {
    Derived() : ShelbyGEQController(0x1337, 0x2468) {}
  };
  Derived controller;
  bool ok = controller.portableChannel() == channel &&
            controller.sourceState().constructorId == baseId &&
            controller.getNumParameters() == 33 &&
            controller.sourceState().descriptors->count() == 33;
  for (float value : controller.portableValues()) {
    unsigned expected;
    ok &= static_cast<bool>(fixture >> expected) &&
          std::bit_cast<unsigned>(value) == expected;
  }
  for (auto value : controller.portableMarkers()) {
    unsigned expected;
    ok &= static_cast<bool>(fixture >> expected) && value == expected;
  }
  for (auto value : controller.portableTimeWords()) {
    unsigned expected;
    ok &= static_cast<bool>(fixture >> expected) && value == expected;
  }
  std::cout << "1 constructor case\n";
  return !ok;
}
