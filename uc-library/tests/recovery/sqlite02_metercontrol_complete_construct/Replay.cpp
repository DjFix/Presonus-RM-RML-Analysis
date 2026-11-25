#include "presonus/surface_panel/MeterControl.hpp"

#include <iostream>

namespace {
using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::MeterControl;
using presonus::surface_panel_port::MeterControlAccess;

#ifdef METER_BASE_CONSTRUCTOR
struct DerivedMeter : MeterControl {
  explicit DerivedMeter(int tag) : MeterControl(tag) {}
};
using TestedMeter = DerivedMeter;
#else
using TestedMeter = MeterControl;
#endif

void observe(Control &control) {
  std::cout << ControlAccess::lastLevel(control) << ' '
            << (control.getParameter() != nullptr) << ' '
            << (control.getAltParameter() != nullptr) << ' '
            << (control.getTertiaryParameter() != nullptr) << ' '
            << (ControlAccess::io(control) != nullptr) << ' '
            << ControlAccess::tag(control);
}
} // namespace

int main() {
  MeterControl defaultMeter;
  if (ControlAccess::tag(defaultMeter) != 0 ||
      MeterControlAccess::direction(defaultMeter) != 0 ||
      MeterControlAccess::overrideCount(defaultMeter) != nullptr)
    return 1;
  int tag;
  while (std::cin >> tag) {
    TestedMeter meter(tag);
    Control provider(tag);
    Control &base = meter;
    if (base.castTo(0x4d43746c) != &meter || base.castTo(0x4374726c) != &base ||
        base.castTo(0) != nullptr)
      return 2;
    observe(base);
    std::cout << ' ' << MeterControlAccess::direction(meter) << ' '
              << (MeterControlAccess::overrideCount(meter) != nullptr) << ' ';
    observe(provider);
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
