#include "presonus/surface_panel/MeterControl.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

using Presonus::Panel::MeterControl;
using presonus::surface_panel_port::MeterControlAccess;
static float floatBits(std::uint32_t bits) {
  float result;
  std::memcpy(&result, &bits, 4);
  return result;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    char operation;
    unsigned role, overridePresent;
    std::uint32_t a, b, direction, overrideValue, expectedReturn,
        expectedDirection;
    std::array<std::uint32_t, 72> before{}, expected{}, actual{};
    std::array<float, 16> inputSteps{}, outputSteps{};
    if (!(row >> operation >> role >> a >> b >> direction >> overridePresent >>
          overrideValue >> expectedReturn >> expectedDirection))
      return 3;
    for (auto &value : before)
      row >> value;
    for (auto *steps : {&inputSteps, &outputSteps})
      for (auto &value : *steps) {
        std::uint32_t bits;
        row >> bits;
        value = floatBits(bits);
      }
    for (auto &value : expected)
      row >> value;
    if (!row)
      return 4;
    std::memcpy(MeterControlAccess::counts(), before.data(), 8);
    std::memcpy(&MeterControlAccess::input(), before.data() + 2, 140);
    std::memcpy(&MeterControlAccess::output(), before.data() + 37, 140);
    int overrideCount;
    std::memcpy(&overrideCount, &overrideValue, 4);
    MeterControl control;
    MeterControlAccess::setState(control,
                                 overridePresent ? &overrideCount : nullptr,
                                 static_cast<std::int32_t>(direction));
    std::uint32_t result = 0;
    switch (operation) {
    case 'S':
      MeterControl::setMeterSteps(
          static_cast<std::int32_t>(a), static_cast<std::int32_t>(b),
          static_cast<std::int32_t>(a) > 0 ? inputSteps.data() : nullptr,
          static_cast<std::int32_t>(b) > 0 ? outputSteps.data() : nullptr);
      break;
    case 'R':
      MeterControl::setDbRange(floatBits(a), floatBits(b));
      break;
    case 'D':
      control.setBusDirection(static_cast<MeterControl::BusDirection>(a));
      break;
    case 'G':
      result = static_cast<std::uint32_t>(control.getNumMeterSteps(
          static_cast<MeterControl::BusDirection>(a), b != 0));
      break;
    default:
      return 5;
    }
    std::memcpy(actual.data(), MeterControlAccess::counts(), 8);
    std::memcpy(actual.data() + 2, &MeterControlAccess::input(), 140);
    std::memcpy(actual.data() + 37, &MeterControlAccess::output(), 140);
    const auto actualDirection =
        static_cast<std::uint32_t>(MeterControlAccess::direction(control));
    if (result != expectedReturn || actualDirection != expectedDirection ||
        actual != expected) {
      std::fprintf(stderr,
                   "Mismatch case %u operation %c role %u return %u/%u "
                   "direction %u/%u\n",
                   cases, operation, role, result, expectedReturn,
                   actualDirection, expectedDirection);
      for (unsigned i = 0; i < actual.size(); ++i)
        if (actual[i] != expected[i])
          std::fprintf(stderr, "word %u %08x/%08x\n", i, actual[i],
                       expected[i]);
      return 1;
    }
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 6;
  std::printf("PASS: %u original ARM MeterControl differential cases\n", cases);
}
