#pragma once
#include "presonus/panel/PresetComponent.hpp"

namespace presonus::panel {
struct GeqPresetState {
  Core::ConstVector<Core::Portable::Component *> equalizers;
  Core::Portable::Parameter *selection = nullptr;
};
} // namespace presonus::panel
namespace Presonus::Panel {
// Partial portable interface. Original declaration, layout and ARM ABI remain
// bounded by existing evidence; this migration changes source organization
// only.
class GeqPresetComponent : public PresetComponent {
public:
  GeqPresetComponent(presonus::panel::PresetApplicationServices &services,
                     presonus::panel::GeqPresetState state)
      : PresetComponent(services), state(state) {}
  ~GeqPresetComponent() override;
  bool recall(Core::Portable::Attributes &, bool);

private:
  presonus::panel::GeqPresetState state;
};
} // namespace Presonus::Panel
