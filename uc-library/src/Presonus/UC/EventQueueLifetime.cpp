#include "presonus/uc/event_queue.hpp"
#include <stdexcept>
namespace presonus::uc {
namespace {
void lockOwned(void *context) {
  static_cast<OwnedEventQueueState *>(context)->lock.value().lock();
}
void unlockOwned(void *context) {
  static_cast<OwnedEventQueueState *>(context)->lock.value().unlock();
}
void *valueOwned(void *context, const Presonus::UC::Event &event,
                 QueueValueKind kind) {
  auto &owner = *static_cast<OwnedEventQueueState *>(context);
  return owner.typedValue(owner.typedContext, event, kind);
}
} // namespace
OwnedEventQueueState::OwnedEventQueueState(void *context,
                                           ValueProvider provider)
    : typedContext(context), typedValue(provider) {
  if (!provider)
    throw std::invalid_argument("live typed queue provider required");
  view.owned = this;
  view.context = this;
  view.lock = lockOwned;
  view.unlock = unlockOwned;
  view.value = valueOwned;
}
void OwnedEventQueueState::attach() {
  if (attached)
    throw std::logic_error("owned queue already attached");
  lock.emplace();
  items.emplace();
  attached = true;
}
void OwnedEventQueueState::append(Presonus::UC::EventItem *item) {
  if (!item)
    throw std::invalid_argument("live unique owned queue item required");
  if (!attached)
    throw std::logic_error("live owned queue facade required");
  Core::Threads::ScopedLock guard(lock.value());
  items.value().append(item);
}
} // namespace presonus::uc
namespace Presonus::UC {
EventQueue::~EventQueue() {
  // Borrowed-state construction is explicitly an independent nonowning API.
  // Original lifecycle readiness excludes that source-only lifetime domain.
  if (state_.owned) {
    flush();
    // Original Queue D1/D2 flush, destroy list, then CoreLock D1. Execute
    // actual pinned CCL destruction here, not at the later sidecar lifetime.
    state_.owned->items.reset();
    state_.owned->lock.reset();
    state_.owned->attached = false;
  }
}
EventItem *EventQueue::retrieveEvent() {
  if (!state_.owned)
    throw std::logic_error("owned queue lifecycle state required");
  Core::Threads::ScopedLock guard(state_.owned->lock.value());
  return state_.owned->items.value().removeFirst();
}
bool EventQueue::isEmpty() const {
  // Original isEmpty reads the head without taking the lock. Only serialized
  // access is claimed; no concurrent query/mutation guarantee is added.
  return state_.owned ? state_.owned->items.value().isEmpty()
                      : state_.head == nullptr;
}
void EventQueue::flush() {
  // removeFirst unlocks before virtual destruction. Payloads may run real
  // destructors; this does not append synthetic deallocation observations.
  while (auto *item = retrieveEvent())
    delete item;
}
} // namespace Presonus::UC
