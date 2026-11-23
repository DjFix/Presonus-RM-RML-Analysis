#include "presonus/mixer/FXComponent.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>

struct Boundary final : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override {
    throw std::runtime_error("unexpected app call");
  }
  std::uint32_t getTypeNumber() override {
    throw std::runtime_error("unexpected app call");
  }
  void updateTypeName() override {
    throw std::runtime_error("unexpected app call");
  }
  void handleTypeChange(bool) override {
    throw std::runtime_error("unexpected app call");
  }
};
int main() {
  static_assert(std::numeric_limits<int>::digits == 31);
  Core::Portable::Component parameters;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.minValue = 0.f;
  info.maxValue = 1.f;
  Core::Portable::NumericParam parameter{info};
  parameter.setValue(0.25f, false);
  Boundary app;
  presonus::mixer_fx::State state{parameters, parameter, parameter, app};
  Presonus::Mixer::FXComponent fx{state};
  int type, index;
  while (std::cin >> type >> index) {
    const bool result =
        fx.isValidParamForType(static_cast<Presonus::EffectType>(type), index);
    if (state.dirty || state.recalledTypePending ||
        parameter.getValue() != 0.25f || parameters.countParameters() != 0)
      throw std::runtime_error("unexpected FX state change");
    std::cout << static_cast<int>(result) << '\n';
  }
}
