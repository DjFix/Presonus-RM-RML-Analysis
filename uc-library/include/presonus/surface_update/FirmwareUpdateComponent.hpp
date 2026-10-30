#pragma once
#include "core/portable/corecomponent.h"

namespace presonus::surface_update {
struct CallbackSourcePort {};
} // namespace presonus::surface_update
namespace Presonus::Surface {
// Partial source port: original complete layout, secondary interface and
// constructor/destructor lifecycle remain unresolved. This construction API is
// an independent adapter, not an original firmware constructor.
class FirmwareUpdateComponent : public Core::Portable::Component {
public:
  FirmwareUpdateComponent(presonus::surface_update::CallbackSourcePort,
                          const Core::Portable::ParamInfo *parameters,
                          int parameterCount,
                          Core::Portable::Parameter *progress);
  // void returns are provisional; ordinary mangling does not encode them.
  void setText(const char *title, const char *message);
  void onProgress(const char *title, const char *message, float progress);
  void dismissAlert();
  void doAlert(const char *alert, const char *title, const char *message);

private:
  Core::Portable::Parameter *progressParameter;
};
} // namespace Presonus::Surface
