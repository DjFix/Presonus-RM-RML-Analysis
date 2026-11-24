#include "presonus/panel/temperature_control.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

namespace {
struct Param final : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  void setNormalized(float, bool) override { std::abort(); }
};

void replay(int value, int seed, bool bound, bool virtualDispatch) {
  using presonus::panel::ControlAccess;
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1;
  info.defaultValue = .5f;
  Param parameter(info);
  Presonus::Panel::TemperatureControl control(
      presonus::panel::TemperatureSourcePort{}, seed);
  auto *expected = bound ? &parameter : nullptr;
  ControlAccess::parameter(control) = expected;
  ControlAccess::lastLevel(control) = seed;
  const int timerCount = ControlAccess::timers().count();

  if (virtualDispatch) {
    Presonus::Panel::Control &base = control;
    base.broadcastValue(value);
  } else {
    control.Presonus::Panel::TemperatureControl::broadcastValue(value);
  }

  const bool unchanged = ControlAccess::parameter(control) == expected &&
                         ControlAccess::altParameter(control) == nullptr &&
                         ControlAccess::tertiaryParameter(control) == nullptr &&
                         ControlAccess::io(control) == nullptr &&
                         ControlAccess::lastLevel(control) == seed &&
                         ControlAccess::tag(control) == seed &&
                         parameter.getNormalized() == .5f &&
                         ControlAccess::timers().count() == timerCount;
  std::cout << unchanged << '\n';
}
} // namespace

int main() {
  int value, seed;
  bool bound, virtualDispatch;
  while (std::cin >> value >> seed >> bound >> virtualDispatch)
    replay(value, seed, bound, virtualDispatch);
  return std::cin.eof() ? 0 : 2;
}
