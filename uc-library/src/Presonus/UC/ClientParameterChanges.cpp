#include "presonus/uc/ClientComponent.hpp"
#include "presonus/uc/ClientRootComponent.hpp"

namespace Presonus::UC {
ClientRootComponent *ClientComponent::getRoot() {
  for (auto *parent = getParent(); parent; parent = parent->getParent())
    if (auto *root = static_cast<ClientRootComponent *>(
            parent->castTo(ClientRootComponent::kTypeID)))
      return root;
  return nullptr;
}

void ClientComponent::paramChanged(Core::Portable::Parameter *parameter,
                                   int msg) {
  Core::Portable::Component::paramChanged(parameter, msg);
  if (auto *root = getRoot())
    root->sendParamChange(*this, parameter, msg);
}
} // namespace Presonus::UC
