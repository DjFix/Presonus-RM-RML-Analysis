#include "presonus/uc/server_registrar.hpp"
#include <cstdlib>
#include <cstring>

namespace presonus::uc {
// Independent initialized-view precondition guards, not original error paths.
static const AvailableServerView &serverView(const ServerRegistrarState &state,
                                             Presonus::UC::Server *identity) {
  for (int index = 0; index < state.allServerViews.count(); ++index)
    if (state.allServerViews.at(index)->identity == identity)
      return *state.allServerViews.at(index);
  std::abort();
}
static const AvailableServerView &
localView(const ServerRegistrarState &state,
          Presonus::UC::LocalServer *identity) {
  for (int index = 0; index < state.allServerViews.count(); ++index)
    if (state.allServerViews.at(index)->localIdentity == identity)
      return *state.allServerViews.at(index);
  std::abort();
}
} // namespace presonus::uc
namespace Presonus::UC {
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
