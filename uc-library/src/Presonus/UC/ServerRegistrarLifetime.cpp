#include "core/portable/coresingleton.h"
#include "presonus/uc/server.hpp"

DEFINE_STATIC_SINGLETON(Presonus::UC::ServerRegistrar)

namespace Presonus::UC {
ServerRegistrar::ServerRegistrar()
    : ownedState_(std::make_unique<presonus::uc::ServerRegistrarState>()),
      state_(*ownedState_) {}
ServerRegistrar &ServerRegistrar::instance() {
  return Core::Portable::StaticSingleton<ServerRegistrar>::instance();
}
ServerRegistrar::~ServerRegistrar() {
  if (!ownedState_)
    return; // Explicit independent borrowed domain.
  const int count = state_.remoteServers.count();
  for (int index = 0; index < count; ++index) {
    auto *view = state_.remoteServers.at(index);
    if (view)
      delete view->identity; // Real virtual D0 and physical deallocation.
  }
  // Correlated view sidecar is borrowed metadata; never delete those objects.
  state_.allServerViews.removeAll();
  state_.listeners.removeAll();
  state_.remoteServers.removeAll();
  state_.localServers.removeAll();
}
bool ServerRegistrar::sourcePortAddOwnedRemote(
    Server *server, presonus::uc::AvailableServerView &view) {
  if (!ownedState_ || !server || server->getType() != 1)
    return false;
  for (int index = 0; index < state_.remoteServers.count(); ++index) {
    const auto *existing = state_.remoteServers.at(index);
    if (existing == &view || (existing && existing->identity == server))
      return false; // Independent unique-ownership precondition.
  }
  view.identity = server;
  if (!state_.remoteServers.add(&view))
    return false;
  if (!state_.allServerViews.add(&view)) {
    state_.remoteServers.remove(&view);
    return false;
  }
  return true;
}
} // namespace Presonus::UC
