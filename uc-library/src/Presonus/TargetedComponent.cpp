#include "presonus/TargetedComponent.hpp"
namespace Presonus {
TargetedComponent::TargetedComponent(const char *name)
    : UC::ServerComponent(name) {}
TargetedComponent::~TargetedComponent() = default;
void TargetedComponent::onIdle() {
  Core::Portable::Component::onIdle();
  if (pendingUpdates_) {
    pendingUpdates_ = 0;
    doUpdates();
    postDoUpdates();
  }
}
void TargetedComponent::doUpdates() {}
void TargetedComponent::postDoUpdates() {}
} // namespace Presonus
