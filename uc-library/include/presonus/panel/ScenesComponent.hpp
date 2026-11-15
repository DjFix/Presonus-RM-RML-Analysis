#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetComponent.hpp"

namespace Presonus::Panel {
class FrontPanelComponent;
// Partial portable interface. Original declaration, layout and ARM ABI remain
// bounded by existing evidence; this migration changes source organization
// only.
class ScenesComponent : public PresetComponent {
public:
  ScenesComponent(presonus::panel::PresetApplicationServices &services,
                  Presonus::Mixer::MixerComponentBase &mixer)
      : PresetComponent(services), mixer(mixer) {}
  ScenesComponent(FrontPanelComponent &, Presonus::Mixer::MixerComponentBase &);
  // Borrowed source-port association; no original layout claim.
  FrontPanelComponent *sourcePortPanel() const { return panel; }
  const Presonus::Mixer::MixerComponentBase &sourcePortMixer() const {
    return mixer;
  }
  ~ScenesComponent() override;
  bool store();

private:
  Presonus::Mixer::MixerComponentBase &mixer;
  FrontPanelComponent *panel = nullptr;
};
} // namespace Presonus::Panel
