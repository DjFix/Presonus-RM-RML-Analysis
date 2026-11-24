#include "presonus/panel/GPIOControlGroup.hpp"
#include "presonus/panel/control.hpp"

#include <array>
#include <iostream>

using Presonus::Panel::Control;
using Presonus::Panel::GPIOControlGroup;
using presonus::panel_binding::ControlGroupAccess;

int main() {
  int id;
  int unused;
  int count;
  while (std::cin >> id >> unused >> count) {
    std::array<Control, 3> controls{Control(31), Control(7), Control(19)};
    if (count < 0 || count > static_cast<int>(controls.size()))
      return 1;
    GPIOControlGroup group(id, unused);
    for (int index = 0; index < count; ++index)
      group.add(&controls[index]);

    if (group.count() != count || ControlGroupAccess::groupId(group) != id ||
        !ControlGroupAccess::ownsState(group))
      return 1;

    group.sort();

    std::cout << group.count() << ' ' << ControlGroupAccess::groupId(group)
              << ' ' << ControlGroupAccess::ownsState(group);
    for (int index = 0; index < count; ++index) {
      auto *control = group.at(index);
      if (control != &controls[index] ||
          group.byTag(presonus::panel::ControlAccess::tag(*control)) != control)
        return 1;
      std::cout << ' ' << presonus::panel::ControlAccess::tag(*control);
    }
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
