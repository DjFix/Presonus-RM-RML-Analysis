#include "presonus/mixer/FXComponent.hpp"

namespace Presonus::Mixer {
void FXComponent::setFxDirty() {
  state_.dirty = true;
  state_.app.setControllerDirty();
}
Core::Portable::ParamValue
FXComponent::mapValues(Core::Portable::Parameter *parameter) {
  return parameter ? parameter->getValue() : 0.f;
}
bool FXComponent::recallFxType() {
  state_.recalledTypeParameter.setValue(
      static_cast<Core::Portable::ParamValue>(state_.app.getTypeNumber()),
      false);
  state_.recalledTypePending = true;
  return true;
}
bool FXComponent::isChildParameter(
    const Core::Portable::Parameter &parameter) const {
  for (int i = 0; i < state_.parameterOwner.countParameters(); ++i)
    if (state_.parameterOwner.getParameterAt(i) == &parameter)
      return true;
  return false;
}
bool FXComponent::refreshFx(bool edit) {
  state_.typeParameter.setValue(state_.recalledTypeParameter.getValue(), false);
  state_.app.updateTypeName();
  state_.app.handleTypeChange(edit);
  return true;
}
} // namespace Presonus::Mixer
