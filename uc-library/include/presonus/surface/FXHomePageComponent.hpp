#pragma once
#include "core/portable/corecomponent.h"
namespace presonus::surface {
struct FXPageTestAccess;
}
namespace Presonus::Surface {
// Partial initialized source port, not original construction or ARM layout.
class FXHomePageComponent : public Core::Portable::Component {
public:
  FXHomePageComponent() = default;
  ~FXHomePageComponent() override;

private:
  friend struct presonus::surface::FXPageTestAccess;
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};
} // namespace Presonus::Surface
