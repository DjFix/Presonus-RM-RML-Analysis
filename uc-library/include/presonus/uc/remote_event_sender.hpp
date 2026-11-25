#pragma once

#include "presonus/uc/connection_interfaces.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include <cstdint>

namespace presonus::uc {
// Independent source-port metadata. The native Connection::addSender assigns
// the remote argument and the dispatcher registration ID to the sender.
struct RemoteEventSenderIDs {
  std::uint32_t remote = 0;
  int local = 0;
};
} // namespace presonus::uc

namespace Presonus::UC {
class RemoteEventSender : public IEventHandler {
public:
  explicit RemoteEventSender(IConnection &);
  virtual ~RemoteEventSender();

  // event must refer to an originally mutable Event. A nonnull context is an
  // live EventItem that satisfies the borrowed connection's queueEvent
  // ownership contract. The connection may destroy it before returning.
  int handleEvent(void *context, const Event &event) override;

  // Independent source-port configuration. The connection stays borrowed.
  presonus::uc::RemoteEventSenderIDs &sourcePortIDs() { return ids_; }

private:
  presonus::uc::RemoteEventSenderIDs ids_;
  IConnection &connection_;
};
} // namespace Presonus::UC
