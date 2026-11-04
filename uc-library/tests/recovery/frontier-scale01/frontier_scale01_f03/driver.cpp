#include "presonus/surface_panel/ControlGroup.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
  using namespace Presonus::Panel;
  using presonus::panel_binding::ControlGroupAccess;
  if (argc != 3)
    return 2;
  int first = static_cast<int>(std::strtoll(argv[1], nullptr, 10));
  int second = static_cast<int>(std::strtoll(argv[2], nullptr, 10));
  ControlGroup group(first, second);
  if (!ControlGroupAccess::ownsState(group) || group.byTag(0) != nullptr)
    return 3;
  // Independent portable regression: borrowed state must remain borrowed.
  presonus::panel_binding::ControlGroupState state;
  ControlGroup borrowed(state);
  if (ControlGroupAccess::ownsState(borrowed))
    return 4;
  borrowed.add(nullptr);
  if (borrowed.count() != 1 || state.controls.count() != 1)
    return 5;
  std::cout << static_cast<std::uint32_t>(ControlGroupAccess::groupId(group))
            << " " << group.count() << "\n";
}
