#include "presonus/panel/FXPage.hpp"
#include <cfloat>
#include <cstdint>
#include <cstring>
#include <iostream>
namespace {
float number(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
} // namespace
int main(int argc, char **argv) {
  const bool providers = argc == 2 && std::strcmp(argv[1], "providers") == 0;
  unsigned present, initial;
  std::uint32_t value, lower, upper;
  while (std::cin >> present >> value >> lower >> upper >> initial) {
    const Core::Portable::ParamInfo info = PARAM_FLOAT(
        0, "value", -FLT_MAX, FLT_MAX, 0.f, 0.f, nullptr, nullptr, 0.f, 0);
    Core::Portable::NumericParam parameter(info);
    parameter.setValue(number(value), false);
    const float observed = parameter.getValue();
    if (providers) {
      std::cout << bits(observed) << '\n';
      continue;
    }
    Presonus::Panel::FXPageState state{present ? &parameter : nullptr,
                                       number(lower), number(upper),
                                       static_cast<std::uint8_t>(initial)};
    Presonus::Panel::FXPage page(state);
    auto *identity = state.parameter;
    page.prepare();
    if (state.parameter != identity || bits(state.lower) != lower ||
        bits(state.upper) != upper ||
        bits(parameter.getValue()) != bits(observed))
      return 3;
    std::cout << static_cast<unsigned>(state.inRange) << '\n';
  }
}
