#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corevector.h"
#include "presonus/DspComponent.hpp"
#include "presonus/mixer/DelayComponent.hpp"
#include <array>
#include <cstdint>

namespace presonus::mixer_fx {
// Independent source-port boundary for app-specific providers not recovered
// here. No original inheritance, object layout, ownership or provider ABI is
// asserted.
struct AppBoundary {
  virtual ~AppBoundary() = default;
  virtual void setControllerDirty() = 0;
  virtual std::uint32_t getTypeNumber() = 0;
  virtual void updateTypeName() = 0;
  virtual void handleTypeChange(bool edit) = 0;
};
struct LoadState {
  Presonus::DspComponent &dsp;
  Core::Portable::Parameter &diagnostic0, &diagnostic1, &diagnostic2;
  bool loading = false;
};
struct InterpolatorState {
  std::array<Core::Portable::Parameter *, 6> parameters{};
  Core::Vector<Core::Portable::Parameter *> deferred;
};
struct State {
  Core::Portable::Component &parameterOwner;
  Core::Portable::Parameter &typeParameter;
  Core::Portable::Parameter &recalledTypeParameter;
  AppBoundary &app;
  bool dirty = false;
  bool recalledTypePending = false;
  LoadState *load = nullptr; // required borrowed binding for load only
  Core::Portable::Parameter *displayedTypeParameter = nullptr;
  InterpolatorState *interpolation = nullptr;
};
} // namespace presonus::mixer_fx

namespace Presonus::Mixer {
// Portable source port with original encoded method identities. State is an
// explicit adaptation; original return declarations and class layout
// unresolved.
// Intentional real CCL base/type-query adaptation; original RTTI is recorded
// separately. Existing borrowed application bindings remain authoritative.
class FXComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x16fd2c, FXComponent, Core::Portable::Component)
  explicit FXComponent(presonus::mixer_fx::State &state) : state_(state) {}
  // Identity conversion observed in ARM; original static return is unresolved.
  virtual std::int32_t getEffectTypeInternal(Presonus::EffectType type);
  // Provisional signed integer return; ordinary mangling omits it.
  std::int32_t getTypeNum() const;
  void setFxDirty();
  void updateFxTypeName();
  void setInterpolator(int parameterIndex, int effectType);
  Core::Portable::ParamValue mapValues(Core::Portable::Parameter *parameter);
  bool recallFxType();
  bool isChildParameter(const Core::Portable::Parameter &parameter) const;
  bool refreshFx(bool edit);
  // Real CCL base constrains this source-port return to bool.
  bool load(const Core::Portable::InputStorage &) override;

private:
  presonus::mixer_fx::State &state_;
};
} // namespace Presonus::Mixer
