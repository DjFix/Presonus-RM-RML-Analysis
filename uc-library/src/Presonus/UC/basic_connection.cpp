#include "presonus/uc/basic_connection_runtime.hpp"
namespace Presonus::UC {
bool BasicConnection::sendEvent(const Event &event) {
  if (state_.queue->updateEvent(event))
    return true;
  EventItem *item = state_.factory->create(event);
  if (!item)
    return false;
  state_.append(state_.context, item);
  return true;
}
bool BasicConnection::queueEvent(void *opaque) {
  if (!opaque)
    return false;
  auto *item = static_cast<EventItem *>(opaque);
  Event &incomingData = item->getData();
  auto binding =
      owned_
          ? presonus::uc::BasicConnectionSourceAccess::bindIncoming(
                *this, *item, incomingData.type)
          : std::optional<presonus::uc::BasicConnectionTypedValues::Binding>{};
  const bool coalesced = state_.queue->updateEvent(incomingData);
  binding.reset(); // Remove source provenance before actual deletion/transfer.
  if (coalesced) {
    delete item;
    return true;
  }
  state_.append(state_.context, item);
  return true;
}
bool BasicConnection::hasQueuedEvents() const {
  return owned_ ? !state_.queue->isEmpty() : state_.storage->head != nullptr;
}
} // namespace Presonus::UC
