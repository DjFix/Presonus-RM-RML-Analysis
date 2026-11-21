#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/mixer/AudioComponent.hpp"
#include <optional>
namespace Presonus::Mixer {
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases. The explicit audio
// lifecycle tag owns a portable AudioComponent subobject, with independent
// C++ layout and pointer identity.
class LPFilterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x173358, LPFilterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  struct SourcePortAudioLifecycle {};
  explicit LPFilterComponent(SourcePortConstruction, const char *name = "")
      : Core::Portable::Component(name) {}
  // Transfers one release obligation for each non-null provider to
  // AudioComponent.
  LPFilterComponent(SourcePortAudioLifecycle, const char *name,
                    Dsp::Controller *controller,
                    Core::IPropertyHandler *handler, int id);
  ~LPFilterComponent() override;

private:
  std::optional<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
