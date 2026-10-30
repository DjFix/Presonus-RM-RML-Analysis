#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/uc/firmware_update_listener.hpp"
namespace presonus::mixer_update {
struct CallbackSourcePort {};
} // namespace presonus::mixer_update
namespace Presonus::Mixer {
// Partial source port only. Independent construction, no original
// layout/lifecycle.
class FirmwareUpdateComponent : public Core::Portable::Component {
public:
  FirmwareUpdateComponent(presonus::mixer_update::CallbackSourcePort,
                          const Core::Portable::ParamInfo *, int,
                          Core::Portable::Parameter *,
                          UC::IFirmwareUpdateListener *);
  // Original ordinary return types remain unencoded; void is provisional.
  void setText(const char *, const char *);
  void onProgress(const char *, const char *, float);
  void dismissAlert();
  void doAlert(const char *, const char *, const char *);

private:
  Core::Portable::Parameter *progressParameter;
  UC::IFirmwareUpdateListener *progressListener;
};
} // namespace Presonus::Mixer
