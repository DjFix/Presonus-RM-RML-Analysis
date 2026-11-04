#pragma once

namespace Presonus::UC {
// Partial portable source model. No original layout or return declaration is
// established. The untyped borrowed pointer is an intentional source-port
// choice.
class NetworkItem {
public:
  explicit NetworkItem(void *borrowedComponent)
      : component_(borrowedComponent) {}
  void *getComponent() const;

private:
  void *component_;
};
} // namespace Presonus::UC
