#include "presonus/mixer/FXComponent.hpp"
#include <cstring>
#include <iostream>
struct Boundary final : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override { std::abort(); }
  std::uint32_t getTypeNumber() override { std::abort(); }
  void updateTypeName() override { std::abort(); }
  void handleTypeChange(bool) override { std::abort(); }
};
int main() {
  Core::Portable::Component owner("FX replay");
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  std::strcpy(info.name, "type");
  info.minValue = -2147483648.f;
  info.maxValue = 2147483520.f;
  std::uint32_t bits;
  while (std::cin >> bits) {
    float value;
    std::memcpy(&value, &bits, sizeof value);
    info.defaultValue = value;
    Core::Portable::NumericParam parameter(info);
    Boundary boundary;
    presonus::mixer_fx::State state{owner, parameter, parameter, boundary};
    Presonus::Mixer::FXComponent fx(state);
    parameter.setValue(value, false);
    auto actual = parameter.getValue();
    std::uint32_t actualBits;
    std::memcpy(&actualBits, &actual, sizeof actual);
    std::cout << actualBits << ' ' << fx.getTypeNum() << '\n';
  }
}
