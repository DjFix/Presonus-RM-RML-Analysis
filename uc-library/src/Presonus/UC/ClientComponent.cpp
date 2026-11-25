#include "presonus/uc/ClientComponent.hpp"

namespace Presonus::UC {
ClientComponent::ClientComponent(const char *name) : Component(name) {}

void *ClientComponent::castTo(int typeId) {
  constexpr int clientComponentType = 0x436c436f;
  return typeId == clientComponentType || typeId == Component::kTypeID
             ? this
             : nullptr;
}

void ClientComponent::notify(const MessageAttributes &) {}
} // namespace Presonus::UC
