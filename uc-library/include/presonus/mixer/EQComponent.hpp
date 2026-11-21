#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/mixer/AudioComponent.hpp"
#include <optional>
namespace Presonus::Mixer {
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases. The explicit audio
// lifecycle tag owns a portable AudioComponent subobject, with independent
// C++ layout and pointer identity.
class EQComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x173488, EQComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  struct SourcePortAudioLifecycle {};
  explicit EQComponent(SourcePortConstruction, const char *name = "")
      : Core::Portable::Component(name) {}
  // Transfers one release obligation for each non-null provider to
  // AudioComponent.
  EQComponent(SourcePortAudioLifecycle, const char *name,
              Dsp::Controller *controller, Core::IPropertyHandler *handler,
              int id);
  ~EQComponent() override;

private:
  std::optional<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
