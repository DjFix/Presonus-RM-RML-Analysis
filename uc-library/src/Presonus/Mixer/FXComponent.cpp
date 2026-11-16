#include "presonus/mixer/FXComponent.hpp"
#include "core/system/coredebug.h"
#include <stdexcept>

namespace Presonus::Mixer {
std::int32_t FXComponent::getEffectTypeInternal(Presonus::EffectType type) {
  return static_cast<std::int32_t>(type);
}

std::int32_t FXComponent::getTypeNum() const {
  return static_cast<std::int32_t>(state_.typeParameter.getValue());
}

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
bool FXComponent::load(const Core::Portable::InputStorage &storage) {
  if (!state_.load)
    throw std::logic_error("FX load requires borrowed native-state providers");
  auto &state = *state_.load;
  Core::DebugPrintf("FXComponent::load start\n");
  state.loading = true;
  Core::Portable::InputStorage adapted(storage.getAttributes(),
                                       storage.getFilter());
  adapted.setMode("ignoreAltMemory");
  const bool result = state.dsp.load(adapted) != 0;
  state.loading = false;
  Core::DebugPrintf("FXComponent::load complete\n");
  const float a = state.diagnostic0.getValue();
  const float b = state.diagnostic1.getValue();
  const float c = state.diagnostic2.getValue();
  Core::DebugPrintf("  loaded values: %1.2f  %1.2f  %1.2f\n", double(a),
                    double(b), double(c));
  return result;
}
} // namespace Presonus::Mixer
