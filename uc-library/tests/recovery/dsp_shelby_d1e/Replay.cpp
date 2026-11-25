#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

namespace {
struct Target final : Core::IPropertyHandler {
  unsigned count = 0;
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { ++count; }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  unsigned expectedRelease, expectedDelete;
  if (!(fixture >> expectedRelease >> expectedDelete) || expectedDelete != 0)
    return 2;
  Target target;
  {
    ShelbyGEQController controller(0x1337, 0x2468);
    controller.setTarget(&target);
    controller.makeTargetOwner();
  }
  std::cout << "1 nondeleting destructor case\n";
  return target.count != expectedRelease;
}
