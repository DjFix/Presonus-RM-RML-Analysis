#include "presonus/uc/connection.hpp"

namespace Presonus::UC {
void Connection::adjustRouting(Event &, bool) {}
bool Connection::sendPeriodicEvent(const Event &) { return false; }
bool Connection::reset() { return false; }
void *Connection::findSender(int id) const {
  for (std::size_t i = 0; i < state_.senderCount; ++i)
    if (state_.senders[i].remoteBits == static_cast<std::uint32_t>(id))
      return state_.senders[i].identity;
  return nullptr;
}
void *Connection::findSenderWithLocalID(int id) const {
  for (std::size_t i = 0; i < state_.senderCount; ++i)
    if (state_.senders[i].localBits == static_cast<std::uint32_t>(id))
      return state_.senders[i].identity;
  return nullptr;
}
void Connection::initChannel() {
  const int granularity = state_.granularity(state_.context);
  // Original uses signed comparison/division. Zero divides are excluded;
  // negative values are retained, even when the resulting capacity is zero.
  state_.channelLimitBits =
      granularity >= 4096
          ? 4096u
          : static_cast<std::uint32_t>((4096 / granularity) * granularity);
}
bool Connection::handleInternal(const Event &event) {
  if (event.type != 19537u)
    return false;
  presonus::uc::ConnectionReplyView reply;
  reply.header = {19538u, 24u, event.routeB, event.routeA};
  reply.payloadWords = state_.queryPayload(state_.context, event);
  state_.sendReply(state_.context, reply);
  return true;
}
} // namespace Presonus::UC
