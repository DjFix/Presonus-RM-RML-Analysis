#pragma once
#include "core/portable/corecomponent.h"
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
struct State {
  Core::Portable::Component &parameterOwner;
  Core::Portable::Parameter &typeParameter;
  Core::Portable::Parameter &recalledTypeParameter;
  AppBoundary &app;
  bool dirty = false;
  bool recalledTypePending = false;
};
} // namespace presonus::mixer_fx

namespace Presonus::Mixer {
// Portable source port with original encoded method identities. State is an
// explicit adaptation; original return declarations and class layout
// unresolved.
class FXComponent {
public:
  explicit FXComponent(presonus::mixer_fx::State &state) : state_(state) {}
  void setFxDirty();
  Core::Portable::ParamValue mapValues(Core::Portable::Parameter *parameter);
  bool recallFxType();
  bool isChildParameter(const Core::Portable::Parameter &parameter) const;
  bool refreshFx(bool edit);

private:
  presonus::mixer_fx::State &state_;
};
} // namespace Presonus::Mixer
