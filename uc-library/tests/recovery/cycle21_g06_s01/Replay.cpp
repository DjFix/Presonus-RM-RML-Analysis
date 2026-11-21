#include "presonus/mixer/FXComponent.hpp"

#include <cstring>
#include <iomanip>
#include <iostream>

namespace {
using namespace Core::Portable;

struct App final : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override {}
  std::uint32_t getTypeNumber() override { return 0; }
  void updateTypeName() override {}
  void handleTypeChange(bool) override {}
};

struct ParameterProbe final : NumericParam {
  ParameterProbe(const ParamInfo &info, int id) : NumericParam(info), id(id) {}
  int id;
  bool capture = false;
  float getValue() const override {
    const auto result = NumericParam::getValue();
    if (capture)
      std::cout << id << ' ' << result << ' ';
    return result;
  }
  void setValue(float value, bool edit) override {
    if (capture)
      std::cout << id << ' ' << value << ' ' << edit << ' ';
    NumericParam::setValue(value, edit);
  }
};
} // namespace

int main() {
  int present;
  float type, recalled;
  while (std::cin >> present >> type >> recalled) {
    ParamInfo number{};
    number.type = ParamInfo::kFloat;
    number.minValue = -4.3e9f;
    number.maxValue = 4.3e9f;
    ParamInfo string{};
    string.type = ParamInfo::kString;
    std::strcpy(string.name, "recallprompt");
    ParameterProbe live(number, 1), shown(number, 2), saved(number, 3);
    live.setValue(type, false);
    shown.setValue(42, false);
    saved.setValue(recalled, false);
    Component owner;
    App app;
    presonus::mixer_fx::State state{owner, live, saved, app};
    state.displayedTypeParameter = &shown;
    Presonus::Mixer::FXComponent fx(state);
    if (present) {
      fx.addParameters(&string, 1);
      fx.lookupParameter("recallprompt")->fromString("previous", false);
    }
    live.capture = shown.capture = saved.capture = true;
    fx.updateFxTypeName();
    const auto *prompt = StringParam::cast(fx.lookupParameter("recallprompt"));
    shown.capture = false;
    std::cout << shown.getValue() << ' '
              << std::quoted(prompt ? prompt->getText().str() : "missing")
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
