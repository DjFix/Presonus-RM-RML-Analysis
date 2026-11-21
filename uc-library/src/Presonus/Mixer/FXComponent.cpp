#include "presonus/mixer/FXComponent.hpp"
#include "core/system/coredebug.h"
#include <memory>
#include <stdexcept>

namespace {
struct FxRange {
  float minimum, midpoint, maximum;
};

// RM 13731 fxParamRanges contains six arrays of 13 triples. The final three
// arrays are populated by the original FX initialization routine.
constexpr std::array<FxRange, 13> fxRanges[] = {
    {{{.29f, .69f, 1.09f},
      {.39f, .79f, 1.59f},
      {.5f, 1.f, 1.79f},
      {.59f, 1.39f, 2.19f},
      {.79f, 1.59f, 2.39f},
      {.79f, 1.59f, 2.5f},
      {.59f, 1.f, 1.79f},
      {1.39f, 2.39f, 5.f},
      {.5f, 1.39f, 4.f},
      {5.f, 645.f, 1285.f},
      {5.f, 645.f, 1285.f},
      {5.f, 645.f, 1285.f},
      {5.f, 645.f, 1285.f}}},
    {{{1.f, 1.f, 1.f},
      {1.f, 12.f, 40.f},
      {1.f, 12.f, 40.f},
      {1.f, 20.f, 50.f},
      {1.f, 24.f, 60.f},
      {10.f, 50.f, 100.f},
      {5.f, 40.f, 80.f},
      {4.f, 35.f, 90.f},
      {1.f, 10.f, 40.f},
      {.25f, 1.f, 2.f},
      {.25f, 1.f, 2.f},
      {.25f, 1.f, 2.f},
      {.25f, 1.f, 2.f}}},
    {{{-16.f, -16.f, -16.f},
      {-25.f, -15.f, -8.f},
      {-22.f, -16.f, -10.f},
      {-35.f, -22.f, -15.f},
      {-35.f, -22.f, -15.f},
      {-40.f, -30.f, -20.f},
      {-24.f, -24.f, -24.f},
      {-40.f, -30.f, -20.f},
      {-17.f, -17.f, -17.f},
      {0.f, .25f, .94f},
      {0.f, .25f, .94f},
      {.25f, 1.f, 2.f},
      {.25f, 1.f, 2.f}}},
    {{{},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {100.f, 800.f, 3000.f},
      {0.f, .25f, .94f},
      {0.f, .25f, .94f}}},
    {{{},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {0.f, 12.f, 24.f},
      {0.f, .25f, .94f},
      {0.f, .5f, 1.f}}},
    {{{},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {},
      {.19f, .69f, 2.f},
      {0.f, .5f, 1.f},
      {}}},
};
} // namespace

namespace Presonus::Mixer {
std::int32_t FXComponent::getEffectTypeInternal(Presonus::EffectType type) {
  return static_cast<std::int32_t>(type);
}

std::int32_t FXComponent::getTypeNum() const {
  return static_cast<std::int32_t>(state_.typeParameter.getValue());
}

void FXComponent::updateFxTypeName() {
  auto *prompt = lookupParameter("recallprompt");
  if (!prompt)
    return;

  if (!state_.displayedTypeParameter)
    throw std::logic_error(
        "The FX recall prompt requires a displayed type parameter");
  state_.displayedTypeParameter->setValue(state_.typeParameter.getValue(),
                                          true);
  const auto type = static_cast<std::uint32_t>(getTypeNum());
  const auto recalled = state_.recalledTypeParameter.getValue();
  prompt->fromString(static_cast<Core::Portable::ParamValue>(type) == recalled
                         ? ""
                         : "(Recall)",
                     false);
}

void FXComponent::setInterpolator(int parameterIndex, int effectType) {
  auto *binding = state_.interpolation;
  if (!binding || parameterIndex < 0 ||
      static_cast<std::size_t>(parameterIndex) >= binding->parameters.size())
    return;

  using Core::Portable::NumericParam;
  auto *parameter = NumericParam::cast(binding->parameters[parameterIndex]);
  if (!parameter)
    return;

  std::unique_ptr<Core::Interpolator> interpolator(
      Core::InterpolatorFactory::create("skew"));
  if (interpolator) {
    const auto normalized = parameter->getNormalized();
    const auto type =
        getEffectTypeInternal(static_cast<EffectType>(effectType));
    const auto &ranges = fxRanges[parameterIndex];
    if (type < 0 || static_cast<std::size_t>(type) >= ranges.size())
      return;
    const auto &range = ranges[type];
    interpolator->setRange(range.minimum, range.maximum, range.midpoint);
    parameter->setMin(range.minimum);
    parameter->setMax(range.maximum);
    parameter->setDefault(range.midpoint);
    parameter->setInterpolator(interpolator.release());
    parameter->setNormalized(normalized, false);
  }

  // The native routine retains the selected parameter after either factory
  // outcome. Original consumers and ownership of this list remain unresolved.
  try {
    binding->deferred.add(parameter);
  } catch (const std::bad_alloc &) {
    // The native vector reports resize failure and keeps the prior list.
  }
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
