#pragma once
#include "core/public/corevector.h"

namespace Presonus::Panel {
class Control;
}

namespace presonus::panel_binding {
struct ControlGroupAccess;
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
  // Source-port storage; original layout and virtual dispatch remain
  // unresolved.
  ControlGroup(int groupId, int unused);
  ControlGroup(const ControlGroup &) = delete;
  ControlGroup &operator=(const ControlGroup &) = delete;
  // Independent borrowed-state injection constructor.
  explicit ControlGroup(presonus::panel_binding::ControlGroupState &state)
      : state_(state) {}
  int count() const;
  Control *at(int index) const;
  Control *byTag(int tag) const;
  void add(Control *control);

private:
  int groupId_ = 0;
  presonus::panel_binding::ControlGroupState ownedState_;
  friend struct presonus::panel_binding::ControlGroupAccess;
  presonus::panel_binding::ControlGroupState &state_;
};
} // namespace Presonus::Panel

namespace presonus::panel_binding {
// Independent source-port inspection; no original symbol or layout claim.
struct ControlGroupAccess {
  static int groupId(const Presonus::Panel::ControlGroup &group) {
    return group.groupId_;
  }
  static bool ownsState(const Presonus::Panel::ControlGroup &group) {
    return &group.state_ == &group.ownedState_;
  }
};
} // namespace presonus::panel_binding
