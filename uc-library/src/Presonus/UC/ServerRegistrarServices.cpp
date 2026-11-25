#include "presonus/uc/server.hpp"
#include <cstdlib>
#include <cstring>

namespace presonus::uc {
// Independent initialized-view precondition guards, not original error paths.
static AvailableServerView &serverView(const ServerRegistrarState &state,
                                       Presonus::UC::Server *identity) {
  for (int index = 0; index < state.allServerViews.count(); ++index)
    if (state.allServerViews.at(index)->identity == identity)
      return *state.allServerViews.at(index);
  std::abort();
}
static AvailableServerView &localView(const ServerRegistrarState &state,
                                      Presonus::UC::LocalServer *identity) {
  for (int index = 0; index < state.allServerViews.count(); ++index)
    if (state.allServerViews.at(index)->localIdentity == identity)
      return *state.allServerViews.at(index);
  std::abort();
}
} // namespace presonus::uc
namespace Presonus::UC {
void ServerRegistrar::add(LocalServer *server) {
  auto &servers = state_.localServers;
  auto &view = presonus::uc::localView(state_, server);
  if (servers.count() < servers.getCapacity() ||
      servers.resize(servers.count() + 1))
    servers.add(&view);
}

void ServerRegistrar::add(RemoteServer *server) {
  auto &servers = state_.remoteServers;
  auto &view = presonus::uc::serverView(state_, server);
  // The owning source-port roster must never delete an identity twice.
  if ((!ownedState_ || !servers.contains(&view)) &&
      (servers.count() < servers.getCapacity() ||
       servers.resize(servers.count() + 1)))
    servers.add(&view);
  notifyServerAdded(server);
}

void ServerRegistrar::remove(LocalServer *server) {
  auto &servers = state_.localServers;
  for (int index = 0; index < servers.count(); ++index) {
    if (servers.at(index)->localIdentity == server) {
      servers.removeAt(index);
      break;
    }
  }
  notifyServerRemoved(server);
}

void ServerRegistrar::remove(RemoteServer *server) {
  auto &servers = state_.remoteServers;
  for (int index = 0; index < servers.count(); ++index) {
    if (servers.at(index)->identity == server) {
      servers.removeAt(index);
      break;
    }
  }
  notifyServerRemoved(server);
}

void ServerRegistrar::removeManuallyAdded(const char *address,
                                          unsigned short port) {
  if (!ownedState_)
    return;
  const char *needle = address ? address : "";
  auto &servers = state_.remoteServers;
  for (int index = servers.count() - 1; index >= 0; --index) {
    auto *view = servers.at(index);
    if (!view->manuallyAdded || std::strcmp(view->remoteAddress, needle) != 0 ||
        view->remotePort != port)
      continue;
    auto *server = RemoteServer::cast(view->identity);
    if (!server)
      std::abort();
    remove(server);
    state_.allServerViews.remove(view);
    delete server;
  }
}

bool ServerRegistrar::hasLocalServers() const {
  return state_.localServers.count() != 0;
}

Server *ServerRegistrar::find(IEventHandler *handler) const {
  for (int index = 0; index < state_.localServers.count(); ++index) {
    const auto *view = state_.localServers.at(index);
    if (view->handler == handler)
      return view->identity;
  }
  return nullptr;
}

Server *ServerRegistrar::find(void *context, bool localOnly) const {
  for (int index = 0; index < state_.localServers.count(); ++index) {
    const auto *view = state_.localServers.at(index);
    if (view->registrationContext == context)
      return view->identity;
  }
  if (!localOnly)
    for (int index = 0; index < state_.remoteServers.count(); ++index) {
      const auto *view = state_.remoteServers.at(index);
      if (view->registrationContext == context)
        return view->identity;
    }
  return nullptr;
}

Server *ServerRegistrar::find(int identifier, bool localOnly) const {
  for (int index = 0; index < state_.localServers.count(); ++index) {
    const auto *view = state_.localServers.at(index);
    if (view->identifier == identifier)
      return view->identity;
  }
  if (!localOnly)
    for (int index = 0; index < state_.remoteServers.count(); ++index) {
      const auto *view = state_.remoteServers.at(index);
      if (view->identifier == identifier)
        return view->identity;
    }
  return nullptr;
}

Server *ServerRegistrar::find(const char *address, unsigned short port,
                              int transport) const {
  const char *needle = address ? address : "";
  for (int index = 0; index < state_.remoteServers.count(); ++index) {
    const auto *view = state_.remoteServers.at(index);
    if (std::strcmp(view->remoteAddress, needle) == 0 &&
        view->remotePort == port && view->remoteTransport == transport)
      return view->identity;
  }
  return nullptr;
}

void ServerRegistrar::notifyServerAdded(Server *server) {
  const auto &view = presonus::uc::serverView(state_, server);
  const int count = state_.listeners.count();
  const ServerInfo info{24, view.strings, view.flags};
  for (int index = 0; index < count; ++index)
    state_.listeners.at(index)->onServerAvailable(view.identifier, info);
}

void ServerRegistrar::notifyServerRemoved(Server *server) {
  const int count = state_.listeners.count();
  if (count == 0)
    return;
  const auto &view = presonus::uc::serverView(state_, server);
  for (int index = 0; index < count; ++index)
    state_.listeners.at(index)->onServerUnavailable(view.identifier);
}

void ServerRegistrar::notifyServerChanged(Server *server) {
  const int count = state_.listeners.count();
  if (count == 0)
    return;
  const auto &view = presonus::uc::serverView(state_, server);
  for (int index = 0; index < count; ++index)
    state_.listeners.at(index)->onServerChanged(view.identifier);
}

void ServerRegistrar::serverRegistered(LocalServer *server) {
  notifyServerAdded(presonus::uc::localView(state_, server).identity);
}
} // namespace Presonus::UC
