#pragma once
#include "presonus/MackieControlModel.hpp"
#include "presonus/PageComponent.hpp"
// Partial source port. The typed constructor uses the observed PageComponent
// base and the pinned CCL parameter collection. Original ARM32 layout is
// unresolved.
namespace Presonus::Surface {
class StartPageComponent : public Presonus::PageComponent {
public:
  // Existing source-port callers supply their own mode parameters.
  StartPageComponent() : PageComponent("", "", 0) {}
  StartPageComponent(const char *name, const char *formName, int tag);
  ~StartPageComponent();

  // Provisional bool declarations. Both mode parameters must be present.
  bool isDawMode() const;
  bool isMidiMode() const;
};
} // namespace Presonus::Surface
