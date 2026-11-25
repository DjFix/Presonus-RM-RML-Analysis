#include "presonus/surface_panel/DigitalPotControl.hpp"

#include <iostream>
#include <optional>
#include <type_traits>

namespace {
using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::DigitalPotControl;
using presonus::panel_binding::DigitalPotEndpoint;
using presonus::panel_binding::DigitalPotState;

#ifdef DIGITAL_POT_BASE_CONSTRUCTOR
class DerivedControl : public DigitalPotControl {
public:
  explicit DerivedControl(int tag) : DigitalPotControl(tag) {}
};
using TestedControl = DerivedControl;
#else
using TestedControl = DigitalPotControl;
#endif

static_assert(std::is_copy_constructible_v<TestedControl>);
static_assert(!std::is_copy_assignable_v<TestedControl>);

void observe(Control &control) {
  std::cout << ControlAccess::lastLevel(control) << ' '
            << (control.getParameter() != nullptr) << ' '
            << (control.getAltParameter() != nullptr) << ' '
            << (control.getTertiaryParameter() != nullptr) << ' '
            << (ControlAccess::io(control) != nullptr) << ' '
            << ControlAccess::tag(control);
}

bool checkBorrowedCopy(int tag) {
  int sent = 0;
  DigitalPotEndpoint endpoint{&sent, [](void *context, const auto &prefix) {
                                *static_cast<int *>(context) =
                                    (prefix[0] << 16) | (prefix[1] << 8) |
                                    prefix[2];
                              }};
  DigitalPotState external{12, tag, &endpoint};
  std::optional<DigitalPotControl> copy;
  {
    DigitalPotControl borrowed(external);
    copy.emplace(borrowed);
  }
  copy->broadcastValue(34);
  const int expected =
      (0x64 << 16) | (static_cast<unsigned char>(tag) << 8) | 34;
  return external.value == 34 && sent == expected;
}
} // namespace

int main() {
  int tag;
  while (std::cin >> tag) {
    std::optional<TestedControl> copy;
    {
      TestedControl control(tag);
      observe(control);
      std::cout << ' ';
      Control provider(tag);
      observe(provider);
      std::cout << ' ';
      copy.emplace(control);
    }
    observe(*copy);
    std::cout << '\n';
    if (!checkBorrowedCopy(tag))
      return 1;
  }
  return std::cin.eof() ? 0 : 2;
}
