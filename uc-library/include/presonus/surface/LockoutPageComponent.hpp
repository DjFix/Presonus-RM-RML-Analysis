#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Surface {
// Portable source model. Native cleanup has a borrowed AliasParam pointer
// vector followed by Component cleanup; offsets and original bases are unknown.
class LockoutPageComponent : public Core::Portable::Component {
public:
  struct SourcePortConstruction {};
  explicit LockoutPageComponent(SourcePortConstruction) {}
  ~LockoutPageComponent() override;
  Core::Vector<Core::Portable::AliasParam *> &portableAliases() {
    return aliases_;
  }

private:
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};
} // namespace Presonus::Surface
