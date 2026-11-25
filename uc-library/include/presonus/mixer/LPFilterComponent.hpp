#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/mixer/AudioComponent.hpp"
#include <memory>
namespace Presonus::Mixer {
// Portable filter component using a composed AudioComponent and CCL.
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
  // Transfers the non-null handler release obligation to AudioComponent.
  LPFilterComponent(const char *name, Core::IPropertyHandler *handler,
                    int controllerId, int channelId);
  ~LPFilterComponent() override;

  AudioComponent *portableAudioComponent() noexcept { return audio_.get(); }

private:
  std::unique_ptr<AudioComponent> audio_;
};
} // namespace Presonus::Mixer
