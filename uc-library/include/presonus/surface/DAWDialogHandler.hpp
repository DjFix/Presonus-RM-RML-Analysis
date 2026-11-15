#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/surface/DawFxPageComponent.hpp"
#include "presonus/surface/MidiMixerHandler.hpp"
namespace Presonus {
class DAWClientComponent;
}
namespace Presonus::Surface {
// Intentional source-port state and inheritance. No original layout claim.
class DAWDialogHandler : public Core::Portable::Component {
public:
  DAWDialogHandler();
  ~DAWDialogHandler();
  // Independent borrowed source-port state. IDAWDialogHandler interface layout
  // and remaining methods are not reconstructed by this constructor scope.
  Presonus::DAWClientComponent *sourcePortDAWComponent() const { return daw_; }

private:
  Presonus::DAWClientComponent *daw_ = nullptr;
};
} // namespace Presonus::Surface
