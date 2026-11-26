#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/connection.hpp"
#include "presonus/uc/remote_event_sender.hpp"
#include <new>
#include <stdexcept>

namespace Presonus::UC {
struct Connection::SourceOwned {
  ConnectionHandler &handler;
  EventDispatcher &dispatcher;
  presonus::uc::BasicQueueStorage incoming;
  EventQueue queue;
  Core::Vector<RemoteEventSender *> senders{0, 5};
  presonus::uc::ConnectionState bridge;
  presonus::uc::ConnectionTransportProvider transport;

  explicit SourceOwned(Connection &connection, ConnectionHandler &handler)
      : handler(handler), dispatcher(presonus::uc::sourceDispatcherSingleton()),
        incoming(presonus::uc::makeBasicQueueStorage(this, resolve)),
        queue(*incoming), transport(connection) {
    bridge.receive = &transport.receive;
    bridge.context = &transport;
    bridge.granularity = [](void *p) {
      return static_cast<presonus::uc::ConnectionTransportProvider *>(p)
          ->channel->getGranularity();
    };
  }

  ~SourceOwned() {
    for (int index = 0; index < senders.count(); ++index)
      unregisterAndDelete(senders.at(index));
  }

  int indexOf(int id, bool byLocalID = false) const {
    for (int index = 0; index < senders.count(); ++index) {
      const auto &ids = senders.at(index)->sourcePortIDs();
      const auto bits =
          byLocalID ? static_cast<std::uint32_t>(ids.local) : ids.remote;
      if (bits == static_cast<std::uint32_t>(id))
        return index;
    }
    return -1;
  }

  void unregisterAndDelete(RemoteEventSender *sender) {
    dispatcher.removeHandler(sender->sourcePortIDs().local);
    delete sender;
  }

  static void *resolve(void *context, const Event &event,
                       presonus::uc::QueueValueKind kind) {
    auto &self = *static_cast<SourceOwned *>(context);
    return presonus::uc::DispatcherSourceAccess::values(self.dispatcher)
        .resolve(event, kind, self.incoming->items.value());
  }
};

Connection::Connection(presonus::uc::ConnectionState &state,
                       presonus::uc::BasicConnectionState &outgoing)
    : BasicConnection(outgoing), state_(state) {}

Connection::Connection(ConnectionHandler &handler, int type)
    : BasicConnection(type),
      owned_(std::make_unique<SourceOwned>(*this, handler)),
      state_(owned_->bridge) {}

Connection::~Connection() = default;

Connection::SourceOwned &Connection::requireOwned() {
  if (!owned_)
    throw std::logic_error("owning Connection required");
  return *owned_;
}

RemoteEventSender *Connection::findOwnedSender(int id, bool byLocalID) const {
  const int index = owned_->indexOf(id, byLocalID);
  return index < 0 ? nullptr : owned_->senders.at(index);
}

RemoteEventSender *Connection::addSender(int id) {
  auto &source = requireOwned();
  auto sender = std::make_unique<RemoteEventSender>(*this);
  sender->sourcePortIDs().remote = static_cast<std::uint32_t>(id);
  if (!source.senders.add(sender.get()))
    throw std::bad_alloc();
  try {
    sender->sourcePortIDs().local =
        source.dispatcher.addHandler(sender.get(), getType() == 2);
  } catch (...) {
    source.senders.removeLast();
    throw;
  }
  return sender.release();
}

void Connection::removeSender(int id) {
  auto &source = requireOwned();
  const int index = source.indexOf(id);
  if (index < 0)
    return; // Portable safe miss. The observed original requires a live match.
  auto *sender = source.senders.at(index);
  source.senders.removeAt(index);
  source.unregisterAndDelete(sender);
}

int Connection::makeLocalID(int id) {
  requireOwned();
  auto *sender = findOwnedSender(id, false);
  return (sender ? sender : addSender(id))->sourcePortIDs().local;
}
} // namespace Presonus::UC

namespace presonus::uc {
Presonus::UC::ConnectionHandler &
ConnectionSourceAccess::handler(Presonus::UC::Connection &connection) {
  return connection.requireOwned().handler;
}

Presonus::UC::EventDispatcher &
ConnectionSourceAccess::dispatcher(Presonus::UC::Connection &connection) {
  return connection.requireOwned().dispatcher;
}

Presonus::UC::EventQueue &
ConnectionSourceAccess::incomingQueue(Presonus::UC::Connection &connection) {
  return connection.requireOwned().queue;
}

OwnedEventQueueState &
ConnectionSourceAccess::incoming(Presonus::UC::Connection &connection) {
  return *connection.requireOwned().incoming;
}

ConnectionTransportProvider &
ConnectionSourceAccess::transport(Presonus::UC::Connection &connection) {
  return connection.requireOwned().transport;
}

int ConnectionSourceAccess::senderCount(Presonus::UC::Connection &connection) {
  return connection.requireOwned().senders.count();
}

Presonus::UC::RemoteEventSender &
ConnectionSourceAccess::senderAt(Presonus::UC::Connection &connection,
                                 int index) {
  auto &senders = connection.requireOwned().senders;
  if (index < 0 || index >= senders.count())
    throw std::out_of_range("Connection sender index");
  return *senders.at(index);
}
} // namespace presonus::uc
