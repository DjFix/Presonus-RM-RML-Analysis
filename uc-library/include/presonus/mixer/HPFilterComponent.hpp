#pragma once
#include "core/portable/corecomponent.h"
#include <memory>
namespace Core {
struct IPropertyHandler;
}
namespace Presonus::Mixer {
class AudioComponent;
// Portable filter component using a composed AudioComponent and CCL.
class HPFilterComponent : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x1733f0, HPFilterComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit HPFilterComponent(SourcePortConstruction, const char *name = "");
  // Independent source-port ownership for the observed AudioComponent cleanup.
  struct AdoptAudioComponent {};
  HPFilterComponent(AdoptAudioComponent, std::unique_ptr<AudioComponent> audio,
                    const char *name = "");
  // Transfers the non-null handler release obligation to AudioComponent.
  HPFilterComponent(const char *name, Core::IPropertyHandler *handler,
                    int controllerId, int channelId);
  ~HPFilterComponent() override;

  AudioComponent *portableAudioComponent() noexcept { return audio_.get(); }

private:
  std::unique_ptr<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
