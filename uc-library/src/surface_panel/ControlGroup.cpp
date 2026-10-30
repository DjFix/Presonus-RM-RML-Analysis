#include "presonus/surface_panel/ControlGroup.hpp"

namespace Presonus::Panel {
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
} // namespace Presonus::Panel
