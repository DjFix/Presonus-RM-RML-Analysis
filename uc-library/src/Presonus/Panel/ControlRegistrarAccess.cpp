#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cassert>
namespace Presonus::Panel {
int ControlRegistrar::count() const {
  assert(groupRegistry_);
  return groupRegistry_->groups.count();
}
ControlGroup *ControlRegistrar::at(int index) const {
  assert(groupRegistry_);
  const auto &groups = groupRegistry_->groups;
  if (index >= 0 && index < groups.count())
    return groups.at(index);
  // Reuse the actual pinned CCL template's error element. The original app
  // reads this named global; no Core implementation is reconstructed here.
  return Core::ConstVector<ControlGroup *>::getError();
}

ControlGroup *ControlRegistrar::findGroup(int groupId) const {
  assert(groupRegistry_);
  const auto &groups = groupRegistry_->groups;
  for (int index = 0; index < groups.count(); ++index) {
    auto *group = groups.at(index);
    if (presonus::panel_binding::ControlGroupAccess::groupId(*group) == groupId)
      return group;
  }
  static ControlGroup emptyGroup(0, 0);
  return &emptyGroup;
}
} // namespace Presonus::Panel
