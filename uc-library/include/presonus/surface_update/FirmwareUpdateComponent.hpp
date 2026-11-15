#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreworker.h"
#include <cstdint>
#include <memory>

namespace presonus::surface_update {
struct CallbackSourcePort {};
struct ConstructionAccess;
} // namespace presonus::surface_update
namespace Presonus::Surface {
// Partial source port: original complete layout, secondary interface and
// destructor lifecycle remain unresolved. The callback overload is an
// independent adapter; the default constructor ports the bounded original setup
// only.
class FirmwareUpdateComponent : public Core::Portable::Component {
public:
  FirmwareUpdateComponent();
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
  // Independent host ownership, not native +0x90 layout or allocation-size ABI.
  std::unique_ptr<Core::Portable::BackgroundWorker> worker;
  // Provisional native +0x94 word; distinct from callback progress binding.
  std::uint32_t observedTaskWord = 0;
  friend struct presonus::surface_update::ConstructionAccess;
};
} // namespace Presonus::Surface
