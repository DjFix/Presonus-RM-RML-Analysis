#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdlib>

namespace presonus::uc {
// Independent consistency guard outside the validated initialized-state domain.
// It supplies no fallback result or guessed original error behavior.
static const HandlerConnectionView &
viewFor(const ConnectionHandlerState &state,
        Presonus::UC::Connection *identity) {
  for (int index = 0; index < state.views.count(); ++index)
    if (state.views.at(index)->identity == identity)
      return *state.views.at(index);
  std::abort();
}
} // namespace presonus::uc
namespace Presonus::UC {
MulticastConnection *ConnectionHandler::getMulticastConnection() {
  return state_.multicastIdentity;
}

unsigned char ConnectionHandler::isListeningEnabled() const {
  return state_.listeningEnabled;
}

Connection *ConnectionHandler::findExternal(IDataChannel *channel) {
  for (int index = 0; index < state_.externalConnections.count(); ++index) {
    auto *connection = state_.externalConnections.at(index);
    if (presonus::uc::viewFor(state_, connection).channel == channel)
      return connection;
  }
  return nullptr;
}

bool ConnectionHandler::isSendingFromExternalConnection(int identifier) const {
  for (int index = 0; index < state_.externalConnections.count(); ++index) {
    const auto &common =
        *presonus::uc::viewFor(state_, state_.externalConnections.at(index))
             .common;
    for (std::size_t sender = 0; sender < common.senderCount; ++sender)
      if (common.senders[sender].localBits ==
          static_cast<std::uint32_t>(identifier))
        return true;
  }
  return false;
}

bool ConnectionHandler::hasEvents(
    const Core::Vector<Connection *> &items) const {
  const int count = items.count();
  for (int index = 0; index < count; ++index) {
    const auto &view = presonus::uc::viewFor(state_, items.at(index));
    if (view.disabled == 0 && view.outgoing->hasQueuedEvents())
      return true;
  }
  return false;
}

bool ConnectionHandler::hasOutgoingEvents() const {
  if (hasEvents(state_.localConnections) ||
      hasEvents(state_.externalConnections))
    return true;
  return state_.multicastOutgoing->hasQueuedEvents();
}

bool NetworkManager::hasOutgoingEvents() {
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  return state_.connectionHandler->hasOutgoingEvents();
}
} // namespace Presonus::UC
