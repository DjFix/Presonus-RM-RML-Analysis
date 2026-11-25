#pragma once
#include "presonus/uc/ServerComponent.hpp"
#include <cstdint>
namespace Presonus {
// Portable source model: pinned CCL owns component children and parameters.
// Tagged construction is independent; original layout and ARM ABI are unknown.
class TargetedComponent : public UC::ServerComponent {
public:
  struct SourcePortConstruction {};
  explicit TargetedComponent(const char *name);
  explicit TargetedComponent(SourcePortConstruction) : TargetedComponent("") {}
  ~TargetedComponent() override;
  void onIdle() override;
  // Exact original default extension hooks have only prologue/return bodies.
  // Void returns and field storage are explicit source-port declarations.
  virtual void doUpdates();
  virtual void postDoUpdates();
  void portableMarkUpdatesPending(std::uint8_t value) {
    pendingUpdates_ = value;
  }
  std::uint8_t portablePendingUpdates() const { return pendingUpdates_; }

private:
  std::uint8_t pendingUpdates_ = 0;
};
} // namespace Presonus
