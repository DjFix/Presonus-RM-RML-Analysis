#pragma once
#include "core/public/corevector.h"

namespace Presonus::Panel {
class Control;
}

namespace presonus::panel_binding {
// Independent source-port storage and read-only tag gateway. No original class
// layout, constructor, Control definition or ARM binary ABI is asserted.
struct ControlGroupState {
  Core::FixedSizeVector<Presonus::Panel::Control *, 256> controls;
  void *context = nullptr;
  int (*tagOf)(void *, const Presonus::Panel::Control *) = nullptr;
};
} // namespace presonus::panel_binding

namespace Presonus::Panel {
class ControlGroup {
public:
  // Independent injection constructor; original (int,int) constructor pending.
  explicit ControlGroup(presonus::panel_binding::ControlGroupState &state)
      : state_(state) {}
  int count() const;
  Control *at(int index) const;
  Control *byTag(int tag) const;
  void add(Control *control);

private:
  presonus::panel_binding::ControlGroupState &state_;
};
} // namespace Presonus::Panel
