#include "presonus/uc/event_dispatcher.hpp"
#include <cstring>
#include <new>
#include <stdexcept>

namespace presonus::uc {
namespace {
int positive(int n) {
  if (n <= 0)
    throw std::invalid_argument("positive CCL hash modulus required");
  return n;
}
} // namespace
int EventDispatcherState::hashIndex(const int &key, int size) {
  const int raw = Presonus::UC::EventDispatcher::hashHandlerKey(key, size);
  return raw < 0 ? raw + size : raw;
}
EventDispatcherState::EventDispatcherState(int modulus)
    : handlers(positive(modulus), hashIndex, nullptr),
      coalescer(coalescerStorage_) {
  coalescerStorage_.context = this;
  coalescerStorage_.lock = [](void *p) {
    auto &s = *static_cast<EventDispatcherState *>(p);
    s.queueLock.lock();
    try {
      s.nodes_.empty();
      Core::ListIterator<Presonus::UC::EventItem *> it(s.queued);
      while (!it.done()) {
        EventQueueNode node{it.next(), nullptr};
        if (!s.nodes_.add(node))
          throw std::bad_alloc();
      }
      for (int i = 0; i < s.nodes_.count(); ++i)
        s.nodes_.at(i).next =
            i + 1 < s.nodes_.count() ? &s.nodes_.at(i + 1) : nullptr;
      s.coalescerStorage_.head = s.nodes_.count() ? &s.nodes_.at(0) : nullptr;
      s.observe(DispatcherAudit::QueueLock);
    } catch (...) {
      s.queueLock.unlock();
      throw;
    }
  };
  coalescerStorage_.unlock = [](void *p) {
    auto &s = *static_cast<EventDispatcherState *>(p);
    s.observe(DispatcherAudit::QueueUnlock);
    s.coalescerStorage_.head = nullptr;
    s.queueLock.unlock();
  };
  coalescerStorage_.value = [](void *p, const Presonus::UC::Event &event,
                               QueueValueKind kind) {
    auto &s = *static_cast<EventDispatcherState *>(p);
    return s.typedValue(s.typedContext, event, kind);
  };
}
void EventDispatcherState::observe(DispatcherAudit stage) const {
  if (audit)
    audit(auditContext, stage);
}
Presonus::UC::EventItem *EventDispatcherState::retrieve() {
  Core::Threads::ScopedLock guard(queueLock);
  observe(DispatcherAudit::QueueLock);
  auto *item = queued.isEmpty() ? nullptr : queued.removeFirst();
  observe(DispatcherAudit::QueueUnlock);
  return item;
}
} // namespace presonus::uc
namespace Presonus::UC {
int EventDispatcher::hashHandlerKey(const int &key, int size) {
  return key % size;
}
bool EventDispatcher::updateEvent(const Event &event) {
  return state_.coalescer.updateEvent(event);
}
bool EventDispatcher::hasEvents() const { return !state_.queued.isEmpty(); }
bool EventDispatcher::isExternalHandler(int key) {
  Core::Threads::ScopedLock guard(state_.handlerLock);
  state_.observe(presonus::uc::DispatcherAudit::HandlerLock);
  bool found = false;
  for (int i = 0; i < state_.externalIDs.count(); ++i)
    if (state_.externalIDs.at(i) == key) {
      found = true;
      break;
    }
  state_.observe(presonus::uc::DispatcherAudit::HandlerUnlock);
  return found;
}
void EventDispatcher::queueEvent(EventItem *item) {
  Core::Threads::ScopedLock guard(state_.queueLock);
  state_.observe(presonus::uc::DispatcherAudit::QueueLock);
  // Original null append is memory-valid only when empty. Nonempty-null,
  // duplicate ownership and prelinked/intrusive alias states are excluded.
  if (item)
    state_.queued.append(item);
  state_.observe(presonus::uc::DispatcherAudit::QueueUnlock);
}
void EventDispatcher::dispatchOne(EventItem *item) {
  Event &event = item->getData();
  Core::Threads::ScopedLock guard(state_.handlerLock);
  state_.observe(presonus::uc::DispatcherAudit::HandlerLock);
  int key;
  static_assert(sizeof(key) == sizeof(event.routeB));
  std::memcpy(&key, &event.routeB, sizeof(key));
  IEventHandler *handler = nullptr;
  if (!state_.handlers.get(handler, key))
    handler = state_.fallback;
  if (!handler || handler->handleEvent(item, event) != 1)
    delete item;
  state_.observe(presonus::uc::DispatcherAudit::HandlerUnlock);
}
void EventDispatcher::dispatchAll() {
  while (auto *item = state_.retrieve())
    dispatchOne(item);
}
} // namespace Presonus::UC
