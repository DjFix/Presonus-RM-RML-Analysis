#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/basic_connection.hpp"
#include "presonus/uc/connection.hpp"
#include <cstdint>

namespace Presonus::UC {
class IDataChannel;
class MulticastConnection;
} // namespace Presonus::UC
namespace presonus::uc {
// Independent sidecar view joining existing source-port components. No original
// Connection inheritance, object layout, field names or ownership is asserted.
// Every connection listed in a queried vector must have exactly one live view.
struct HandlerConnectionView {
  Presonus::UC::Connection *identity = nullptr;
  Presonus::UC::BasicConnection *outgoing = nullptr;
  ConnectionState *common = nullptr;
  Presonus::UC::IDataChannel *channel = nullptr;
  unsigned char disabled = 0;
};
struct ConnectionHandlerState {
  Core::Vector<Presonus::UC::Connection *> localConnections;
  Core::Vector<Presonus::UC::Connection *> externalConnections;
  Core::Vector<HandlerConnectionView *> views;
  Presonus::UC::MulticastConnection *multicastIdentity = nullptr;
  Presonus::UC::BasicConnection *multicastOutgoing = nullptr;
  unsigned char listeningEnabled = 0;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Only source-port construction is supplied. Original lifecycle and private
// declarations remain unresolved. Ordinary return spellings are choices.
class ConnectionHandler {
public:
  explicit ConnectionHandler(presonus::uc::ConnectionHandlerState &state)
      : state_(state) {}
  MulticastConnection *getMulticastConnection();
  unsigned char isListeningEnabled() const;
  Connection *findExternal(IDataChannel *);
  bool isSendingFromExternalConnection(int) const;
  bool hasEvents(const Core::Vector<Connection *> &) const;
  bool hasOutgoingEvents() const;

private:
  presonus::uc::ConnectionHandlerState &state_;
};
} // namespace Presonus::UC
