#pragma once
#include "presonus/surface/PresetsPageComponent.hpp"
namespace presonus::surface {
// Borrowed mixer GEQ components for the portable preset page. Original mixer
// layout, ownership and return declarations remain unresolved.
struct GeqPresetTargets {
  const Core::Vector<Core::Portable::Component *> &mixGeqs;
  Core::Portable::Component *mainGeq;
  Core::Portable::Component *alternateMainGeq;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Partial source-port inheritance expresses the observed common cleanup only.
// It does not establish original inheritance, constructors, layout or ARM ABI.
class GeqPresetsPageComponent : public PresetsPageComponent {
public:
  using PresetsPageComponent::PresetsPageComponent;
  GeqPresetsPageComponent(
      presonus::surface::PresetsPageState &state,
      presonus::surface::PresetsPageDependencies &dependencies,
      const presonus::surface::GeqPresetTargets &targets)
      : PresetsPageComponent(state, dependencies), targets_(&targets) {}
  ~GeqPresetsPageComponent() override;
  void onShow(bool);
  void getTargetUrl(Core::CString256 &);
  void paramChanged(Core::Portable::Parameter *, int) override;

private:
  const presonus::surface::GeqPresetTargets *targets_ = nullptr;
};
} // namespace Presonus::Surface
