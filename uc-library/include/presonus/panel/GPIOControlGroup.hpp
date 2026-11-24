#pragma once

#include "presonus/surface_panel/ControlGroup.hpp"

namespace Presonus::Panel {
class GPIOControlGroup : public ControlGroup {
public:
  // Portable receiver ancestry and constructor forwarding.
  GPIOControlGroup(int groupId, int unused) : ControlGroup(groupId, unused) {}

  // Portable void declaration for the observed no-op. ARM layout and
  // virtual dispatch are outside this source port.
  void sort();
};
} // namespace Presonus::Panel
