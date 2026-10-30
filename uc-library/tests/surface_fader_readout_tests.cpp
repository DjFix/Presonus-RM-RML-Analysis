#include "presonus/surface_panel/ControlHelpers.hpp"

#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>

namespace {
Core::Portable::ParamInfo info(int tag, const char *name) {
  Core::Portable::ParamInfo value{};
  value.type = Core::Portable::ParamInfo::kFloat;
  value.tag = tag;
  std::strncpy(value.name, name, sizeof(value.name) - 1);
  value.minValue = -2147483648.f;
  value.maxValue = 2147483520.f;
  return value;
}
} // namespace

int main(int argc, char **argv) {
  assert(argc == 2);
  std::size_t cases = 0;
  for (bool reverse : {false, true}) {
    // Metadata outlives the owning actual CCL list and its actual parameters.
    const auto speedInfo = info(900, "speed");
    const auto sensitivityInfo = info(901, "sensitivity");
    Core::Portable::ParamList parameters;
    auto *speed = new Core::Portable::NumericParam(speedInfo);
    auto *sensitivity = new Core::Portable::NumericParam(sensitivityInfo);
    parameters.add(reverse ? sensitivity : speed);
    parameters.add(reverse ? speed : sensitivity);
    Presonus::Surface::PanelRegistrar registrar(parameters);
    std::ifstream input(argv[1]);
    assert(input);
    int tag = 0;
    std::uint32_t bits = 0;
    int expected = 0;
    while (input >> tag >> bits >> expected) {
      assert(tag == 900 || tag == 901);
      float value = 0;
      std::memcpy(&value, &bits, sizeof(value));
      speed->setValueFast(tag == 900 ? value : -77.75f);
      sensitivity->setValueFast(tag == 901 ? value : -77.75f);
      assert(registrar.getFaderSpeed() == (tag == 900 ? expected : -77));
      assert(registrar.getFaderSensitivity() == (tag == 901 ? expected : -77));
      ++cases;
    }
    assert(input.eof());
    // Prove that the independent adapter borrows and queries the live list.
    parameters.remove(speed);
    delete speed;
    speed = new Core::Portable::NumericParam(speedInfo);
    parameters.add(speed);
    speed->setValueFast(-54.625f);
    assert(registrar.getFaderSpeed() == -54);
  }
  assert(cases == 4096);
  std::cout << "PASS4096 fader readout cases; two live-list replacements\n";
}
