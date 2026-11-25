#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus::Mixer {
// The pinned CCL Component supplies the parameter-observer interface.
class GEQLinkHandler : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  // Parameters are borrowed. Detach the observer before destroying a handler
  // whose source is still live.
  GEQLinkHandler(Core::Portable::Parameter *destination,
                 Core::Portable::Parameter *source);
  ~GEQLinkHandler() override;
  void paramChanged(Core::Portable::Parameter *, int) override;

private:
  Core::Portable::Parameter *destination_{};
  Core::Portable::Parameter *source_{};
};
} // namespace Presonus::Mixer
