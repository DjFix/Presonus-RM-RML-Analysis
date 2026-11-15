#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Actual provider source port; ordinary original return/layout remain pending.
class MixSettingsPageComponent : public Core::Portable::Component {
public:
  using Component::Component;
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
};
} // namespace Presonus::Surface
