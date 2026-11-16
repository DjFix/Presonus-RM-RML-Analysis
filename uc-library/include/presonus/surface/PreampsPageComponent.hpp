#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Portable source model: pinned CCL owns component children and parameters.
// Tagged construction is independent; original layout and ARM ABI are unknown.
class PreampsPageComponent : public Core::Portable::Component {
public:
  struct SourcePortConstruction {};
  explicit PreampsPageComponent(SourcePortConstruction)
      : Core::Portable::Component() {}
  ~PreampsPageComponent() override;
};
} // namespace Presonus::Surface
