#include "presonus/panel/temperature_control.hpp"

#include <charconv>
#include <iostream>
#include <string_view>

namespace {
using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::TemperatureControl;
using presonus::panel::TemperatureSourcePort;

struct DerivedTemperatureControl : TemperatureControl {
  explicit DerivedTemperatureControl(int tag) : TemperatureControl(tag) {}
};

void observe(Control &control, bool temperature) {
  std::cout << ControlAccess::tag(control) << ' '
            << ControlAccess::lastLevel(control) << ' '
            << (control.getParameter() != nullptr) << ' '
            << (control.getAltParameter() != nullptr) << ' '
            << (control.getTertiaryParameter() != nullptr) << ' '
            << (ControlAccess::io(control) != nullptr) << ' '
            << (control.Control::castTo(0x4374726c) == &control) << ' '
            << (control.castTo(0x54656d43) ==
                (temperature ? static_cast<void *>(
                                   static_cast<TemperatureControl *>(&control))
                             : nullptr))
            << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view mode(argv[1]);
  const std::string_view argument(argv[2]);
  int tag = 0;
  const auto parsed = std::from_chars(argument.begin(), argument.end(), tag);
  if (parsed.ec != std::errc{} || parsed.ptr != argument.end())
    return 2;
  if (mode == "C1") {
    TemperatureControl control(tag);
    observe(control, true);
  } else if (mode == "C2") {
    DerivedTemperatureControl control(tag);
    observe(control, true);
  } else if (mode == "control") {
    Control control(tag);
    observe(control, false);
  } else if (mode == "tagged") {
    TemperatureControl control(TemperatureSourcePort{}, tag);
    observe(control, true);
  } else {
    return 2;
  }
}
