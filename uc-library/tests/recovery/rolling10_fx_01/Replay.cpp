#include "presonus/mixer/FXComponent.hpp"
#include <cstring>
#include <iostream>
#include <stdexcept>
struct App : presonus::mixer_fx::AppBoundary {
  unsigned calls = 0;
  void setControllerDirty() override { ++calls; }
  std::uint32_t getTypeNumber() override {
    ++calls;
    return 4;
  }
  void updateTypeName() override { ++calls; }
  void handleTypeChange(bool) override { ++calls; }
};
int main() {
  std::uint32_t bits;
  while (std::cin >> bits) {
    Core::Portable::Component owner("owner");
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.maxValue = 1.f;
    Core::Portable::NumericParam type(info), recalled(info);
    type.setValue(.25f, false);
    recalled.setValue(.75f, false);
    App app;
    presonus::mixer_fx::State state{owner, type, recalled, app, true, true};
    Presonus::Mixer::FXComponent component(state);
    std::int32_t value;
    std::memcpy(&value, &bits, sizeof(value));
    auto result = component.getEffectTypeInternal(
        static_cast<Presonus::EffectType>(value));
    if (!state.dirty || !state.recalledTypePending || app.calls ||
        type.getValue() != .25f || recalled.getValue() != .75f ||
        owner.countChildren() != 0 || owner.countParameters() != 0)
      throw std::runtime_error("identity method changed source-port state");
    std::uint32_t output;
    std::memcpy(&output, &result, sizeof(output));
    std::cout << output << '\n';
  }
}
