#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/panel/control.hpp"

namespace Presonus::Panel {
ControlGroup::ControlGroup(int groupId, int)
    : groupId_(groupId), state_(ownedState_) {
  ownedState_.tagOf = [](void *, const Control *control) {
    return presonus::panel::ControlAccess::tag(*const_cast<Control *>(control));
  };
}

ControlGroup::~ControlGroup() {
  for (int index = 0; index < ownedState_.controls.count(); ++index) {
    if (ownedSlots_.test(index))
      delete ownedState_.controls.at(index);
  }
}

int ControlGroup::count() const { return state_.controls.count(); }

Control *ControlGroup::at(int index) const { return state_.controls.at(index); }

Control *ControlGroup::byTag(int tag) const {
  if (tag < state_.controls.count()) {
    Control *control = state_.controls.at(tag);
    if (control && state_.tagOf(state_.context, control) == tag)
      return control;
  }
  for (int index = 0; index < state_.controls.count(); ++index) {
    Control *control = state_.controls.at(index);
    if (state_.tagOf(state_.context, control) == tag)
      return control;
  }
  return nullptr;
}

void ControlGroup::add(Control *control) {
  if (state_.controls.count() <= 255)
    state_.controls.add(control);
}
void ControlGroup::resetParameters() {
  for (auto *control : state_.controls)
    control->setParameter(nullptr, 0);
}

void ControlGroup::resetParameterValues() {
  for (auto *control : state_.controls)
    if (auto *parameter = control->getParameter())
      parameter->resetValue(true);
}

void ControlGroup::sort() {}

void ControlGroup::onIdle() {}
} // namespace Presonus::Panel

namespace presonus::panel_binding {
bool ControlGroupAccess::addOwned(
    Presonus::Panel::ControlGroup &group,
    std::unique_ptr<Presonus::Panel::Control> &&control) {
  if (!ownsState(group) || group.ownedState_.controls.isFull())
    return false;
  const int index = group.ownedState_.controls.count();
  if (!group.ownedState_.controls.add(control.get()))
    return false;
  group.ownedSlots_.set(index);
  control.release();
  return true;
}
} // namespace presonus::panel_binding
