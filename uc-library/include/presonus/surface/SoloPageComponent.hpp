#pragma once

#include "core/portable/corecomponent.h"

namespace Presonus {
class MixerClientComponentBase;
}

namespace Presonus::Surface {

// Portable lifetime model. The alias list stores borrowed pointers. The
// component tree owns registered children and parameters through pinned CCL.
// This interface does not reproduce the original class layout.
class SoloPageComponent : public Core::Portable::Component {
public:
  ~SoloPageComponent() override;
  // Borrow the established mixer client while using its channel groups.
  void bindMixerClient(MixerClientComponentBase &mixer) { mixer_ = &mixer; }
  void clearSolos();
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  bool addAliasReference(Core::Portable::AliasParam &alias);

private:
  MixerClientComponentBase *mixer_ = nullptr;
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};

} // namespace Presonus::Surface
