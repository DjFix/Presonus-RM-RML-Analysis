#pragma once
#include "core/portable/corecomponent.h"
#include <memory>
namespace Presonus::Mixer {
class AudioComponent;
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases; no original
// lifecycle/layout claim.
class LimiterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x1732c8, LimiterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit LimiterComponent(SourcePortConstruction, const char *name = "");
  // Independent source-port ownership for the observed AudioComponent cleanup.
  struct AdoptAudioComponent {};
  LimiterComponent(AdoptAudioComponent, std::unique_ptr<AudioComponent> audio,
                   const char *name = "");
  ~LimiterComponent() override;

private:
  std::unique_ptr<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
