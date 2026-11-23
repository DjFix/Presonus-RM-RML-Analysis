#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include <array>
#include <cstddef>
#include <cstdio>

namespace {
using Presonus::Panel::Control;
using Presonus::Panel::ControlGroup;
using presonus::panel_binding::ControlGroupAccess;
using presonus::panel_binding::ControlGroupState;

bool verify(ControlGroup &group, ControlGroupState *borrowed, bool populated) {
  // Opaque addresses test registry identity only. The replay never dereferences
  // any of these addresses or calls a Control provider.
  alignas(Control) std::byte first[sizeof(Control)]{};
  alignas(Control) std::byte second[sizeof(Control)]{};
  auto *a = reinterpret_cast<Control *>(first);
  auto *b = reinterpret_cast<Control *>(second);
  const std::array<Control *, 3> entries{b, a, b};
  if (populated)
    for (auto *entry : entries)
      group.add(entry);

  const int count = populated ? static_cast<int>(entries.size()) : 0;
  const int id = ControlGroupAccess::groupId(group);
  group.ControlGroup::onIdle();
  if (ControlGroupAccess::ownsState(group) != (borrowed == nullptr) ||
      ControlGroupAccess::groupId(group) != id || group.count() != count ||
      (borrowed && borrowed->controls.count() != count))
    return false;
  for (int index = 0; index < count; ++index)
    if (group.at(index) != entries[index] ||
        (borrowed && borrowed->controls.at(index) != entries[index]))
      return false;

  std::printf("%s-%s\n", borrowed ? "borrowed" : "owned",
              populated ? "populated" : "empty");
  return true;
}
} // namespace

int main() {
  for (bool populated : {false, true}) {
    ControlGroup owned(41, 0);
    ControlGroupState state;
    ControlGroup borrowed(state);
    if (!verify(owned, nullptr, populated) ||
        !verify(borrowed, &state, populated))
      return 1;
  }
}
