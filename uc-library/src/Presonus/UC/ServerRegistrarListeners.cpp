#include "presonus/uc/server_registrar.hpp"

namespace Presonus::UC {
bool ServerRegistrar::hasListeners() const {
  return state_.listeners.count() != 0;
}

void ServerRegistrar::removeListener(INetworkListener *listener) {
  state_.listeners.remove(listener);
}

void ServerRegistrar::addListener(INetworkListener *listener) {
  // The original invokes notification even when its vector resize fails.
  state_.listeners.add(listener);
  notifyAvailable(listener);
}

void ServerRegistrar::notifyAvailable(INetworkListener *listener) {
  const int localCount = state_.localServers.count();
  for (int index = 0; index < localCount; ++index) {
    const auto *server = state_.localServers.at(index);
    if (!server->hidden) {
      const ServerInfo info{24, server->strings, server->flags};
      listener->onServerAvailable(server->identifier, info);
    }
  }
  const int remoteCount = state_.remoteServers.count();
  for (int index = 0; index < remoteCount; ++index) {
    const auto *server = state_.remoteServers.at(index);
    const ServerInfo info{24, server->strings, server->flags};
    listener->onServerAvailable(server->identifier, info);
  }
}
} // namespace Presonus::UC
