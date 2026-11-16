#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Portable source model; original complete layout and ARM ABI are unknown.
class StChannelSettingsPageComponent : public Core::Portable::Component {
public:
  struct SourcePortConstruction {};
  explicit StChannelSettingsPageComponent(SourcePortConstruction) {}
  void paramChanged(Core::Portable::Parameter *, int) override;
};
} // namespace Presonus::Surface
