#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetComponent.hpp"

namespace Presonus::Panel {
// Partial portable interface. Original declaration, layout and ARM ABI remain
// bounded by existing evidence; this migration changes source organization
// only.
class ScenesComponent : public PresetComponent {
public:
  ScenesComponent(presonus::panel::PresetApplicationServices &services,
                  Presonus::Mixer::MixerComponentBase &mixer)
      : PresetComponent(services), mixer(mixer) {}
  ~ScenesComponent() override;
  bool store();

private:
  Presonus::Mixer::MixerComponentBase &mixer;
};
} // namespace Presonus::Panel
