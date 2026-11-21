#pragma once
#include "core/portable/corecomponent.h"
#include <memory>
namespace Presonus::Mixer {
class AudioComponent;
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases; no original
// lifecycle/layout claim.
class HPFilterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x1733f0, HPFilterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit HPFilterComponent(SourcePortConstruction, const char *name = "");
  // Independent source-port ownership for the observed AudioComponent cleanup.
  struct AdoptAudioComponent {};
  HPFilterComponent(AdoptAudioComponent, std::unique_ptr<AudioComponent> audio,
                    const char *name = "");
  ~HPFilterComponent() override;

private:
  std::unique_ptr<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
