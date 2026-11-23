#include "presonus/surface/DisplayManager.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cstring>
#include <iostream>
namespace {

using namespace Presonus;
using namespace Presonus::Panel;
using namespace Core::Portable;
constexpr ParamInfo numericInfo =
    PARAM_FLOAT_(1, "focus", 0, 1, 0, 0, "", "", 0, 0, "", "");
constexpr ParamInfo labelInfo = PARAM_STRING(2, "label", 0);
constexpr ParamInfo aliasInfo = PARAM_ALIAS(3, "alias", 0);
class Handler final : public MixerAssignmentHandler {
public:
  const char *getName() const override { return "focus"; }
  void updateConnections() override {}
  void onMappingParamChanged(Parameter *) override {}
  bool getParamFocusInfo(FocusInfo &info, Parameter *parameter) override {
    ++observations;
    if (parameter != expected)
      return false;
    info.sourcePort.label = "Control";
    return true;
  }
  Parameter *expected = nullptr;
  int observations = 0;
};
} // namespace

namespace {
template <class T> auto snapshot(const T &value) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &value, bytes.size());
  return bytes;
}
} // namespace
int main() {
  ControlRegistrar registrar;
  ControlRegistrar::Delegate defaults;
  SwitchControl control(2, 0, false);
  NumericParam parameter(numericInfo);
  StringParam label(labelInfo);
  AliasParam alias(aliasInfo);
  Handler handler;
  handler.expected = &parameter;
  Core::Vector<AssignmentHandler *> handlers(1);
  handlers.add(&handler);
  presonus::surface::FocusState focusState{&alias, &label, &handlers};
  presonus::surface::RootServices services;
  services.focus = &focusState;
  Surface::SurfaceRootComponent root;
  root.bindServices(services);
  control.setParameter(&parameter, 0);
  const int inputs[][2] = {{0, 0}, {-1, -2147483647 - 1}, {1, 17}};
  for (auto &input : inputs) {
    int group = input[0], index = input[1];
    const auto before = snapshot(registrar);
    const auto receiver = snapshot(defaults);
    const auto controlBefore = snapshot(control);
    defaults.switchChanged(registrar, group, index, false, &control);
    if (parameter.getValue() != 0.f || handler.observations != 0)
      return 2;
    if (before != snapshot(registrar) || receiver != snapshot(defaults) ||
        controlBefore != snapshot(control))
      return 5;
    std::cout << "no-effect\n";
  }
  ControlRegistrar::Delegate &typed = root;
  typed.switchChanged(registrar, 1, 2, false, &control);
  if (handler.observations != 0)
    return 3;
  typed.switchChanged(registrar, 1, 2, true, &control);
  char text[32] = {};
  label.toString(text, sizeof(text));
  if (handler.observations != 1 || alias.getOriginal() != &parameter ||
      std::strcmp(text, "Control"))
    return 4;
  control.setParameter(nullptr, 0);
}
