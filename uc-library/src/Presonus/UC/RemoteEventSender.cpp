#include "presonus/uc/remote_event_sender.hpp"

namespace Presonus::UC {
RemoteEventSender::RemoteEventSender(IConnection &connection)
    : connection_(connection) {}

RemoteEventSender::~RemoteEventSender() = default;

int RemoteEventSender::handleEvent(void *context, const Event &event) {
  const_cast<Event &>(event).routeB = ids_.remote;
  connection_.queueEvent(context);
  return 1;
}
} // namespace Presonus::UC
