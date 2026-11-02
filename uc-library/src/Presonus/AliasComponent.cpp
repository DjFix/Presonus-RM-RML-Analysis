#include "presonus/AliasComponent.hpp"

namespace Presonus {

AliasComponent::AliasComponent(const char *name)
    : Core::Portable::Component(name), original(nullptr) {}

} // namespace Presonus
