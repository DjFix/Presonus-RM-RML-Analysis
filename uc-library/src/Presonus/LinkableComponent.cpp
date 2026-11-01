#include "presonus/LinkableComponent.hpp"
namespace Presonus {
void LinkableComponent::linkAsSlave(LinkableComponent &partner) {
  if (state_.partner != &partner) {
    state_.slave = 1;
    state_.partner = &partner;
  }
}
void LinkableComponent::setLink(LinkableComponent &partner, bool inverse) {
  if (state_.partner == &partner)
    return;
  if (inverse)
    boundary_.set(partner, *this, false);
  else
    boundary_.master(*this, partner);
}
void LinkableComponent::removeLink() {
  if (!state_.partner)
    return;
  auto *partner = state_.partner;
  state_.partner = nullptr;
  boundary_.remove(*partner);
  // Native snapshots the child array and count after partner removal.
  auto *children = state_.children;
  auto count = state_.count;
  for (std::size_t i = 0; i < count; ++i)
    if (children[i])
      if (auto *child = boundary_.query(*children[i], 1282304865U))
        boundary_.remove(*child);
  state_.slave = 0;
}
void LinkableComponent::setLinkEnabled(bool enabled) {
  // Native snapshots count before writing enabled, then obtains child array.
  auto count = state_.count;
  state_.enabled = enabled;
  auto *children = state_.children;
  for (std::size_t i = 0; i < count; ++i)
    if (children[i])
      if (auto *child = boundary_.query(*children[i], 1282304865U))
        child->setLinkEnabled(enabled);
}
bool LinkableComponent::isLinked() const { return state_.partner != nullptr; }
} // namespace Presonus
