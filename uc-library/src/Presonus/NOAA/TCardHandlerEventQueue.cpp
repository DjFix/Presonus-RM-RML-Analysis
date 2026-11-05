#include "core/public/corelinkedlist.h"
#include "core/system/coreatomicstack.h"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include <limits>
#include <stdexcept>
namespace presonus::noaa {
struct CardHandlerEventQueue::Impl {
  struct Slot : Core::AtomicStackLocked::Element {
    std::optional<CardHandlerEvent> event;
    unsigned pool = 0;
  };
  struct Pool {
    Core::AtomicStackLocked free;
    std::unique_ptr<Slot[]> slots;
    explicit Pool(unsigned n) : slots(new Slot[n]) {
      for (unsigned i = 0; i < n; ++i)
        free.push(&slots[i]);
    }
  };
  Core::Threads::Lock mainLock, queueLock;
  Core::LinkedList<Slot *> fifo;
  Pool small, medium, large;
  std::atomic<std::uint32_t> count{0};
  std::atomic<unsigned> nodes{0};
  Impl(unsigned s, unsigned m, unsigned l) : small(s), medium(m), large(l) {}
  Pool &pool(unsigned i) { return i == 0 ? small : i == 1 ? medium : large; }
  static unsigned classify(int bytes) {
    if (bytes <= 0 || bytes > 512)
      throw std::invalid_argument("Handler event semantic size must be 1..512");
    return bytes <= 16 ? 0 : bytes <= 32 ? 1 : 2;
  }
  void recycle(Slot *s) {
    s->event->property.type = 0;
    s->event.reset();
    pool(s->pool).free.push(s);
    count.fetch_sub(1, std::memory_order_release);
  }
  ~Impl() {
    while (!fifo.isEmpty()) {
      auto *s = fifo.removeFirst();
      if (s)
        recycle(s);
    }
    // AtomicStackLocked does not own elements. Discard its head before owned
    // arrays die. LinkedList removeFirst already deleted each link.
    small.free.flush();
    medium.free.flush();
    large.free.flush();
  }
};
CardHandlerEventQueue::CardHandlerEventQueue(unsigned s, unsigned m, unsigned l)
    : impl_([=] {
        if (static_cast<std::uint64_t>(s) + m + l >
            std::numeric_limits<std::uint32_t>::max())
          throw std::invalid_argument(
              "Handler pool capacity exceeds count range");
        return std::make_unique<Impl>(s, m, l);
      }()) {}
CardHandlerEventQueue::~CardHandlerEventQueue() = default;
bool CardHandlerEventQueue::enqueue(const CardHandlerEvent &event) {
  auto index = Impl::classify(event.semanticBytes);
  Core::Threads::ScopedLock main(impl_->mainLock);
  Core::Threads::ScopedLock queue(impl_->queueLock);
  auto *slot = static_cast<Impl::Slot *>(impl_->pool(index).free.pop());
  if (!slot)
    return false;
  slot->pool = index;
  try {
    slot->event.emplace(event);
    if (slot->event->rate)
      slot->event->rate->property = nullptr;
    if (slot->event->routes)
      slot->event->routes->property = nullptr;
    impl_->fifo.append(slot);
  } catch (...) {
    slot->event.reset();
    impl_->pool(index).free.push(slot);
    throw;
  }
  impl_->count.fetch_add(1, std::memory_order_release);
  impl_->nodes.fetch_add(1, std::memory_order_release);
  return true;
}
void CardHandlerEventQueue::enqueueNull() {
  Core::Threads::ScopedLock main(impl_->mainLock);
  Core::Threads::ScopedLock queue(impl_->queueLock);
  impl_->fifo.append(nullptr);
  impl_->nodes.fetch_add(1, std::memory_order_release);
}
void CardHandlerEventQueue::bind(CardHandlerState &state) {
  if ((state.eventQueue && state.eventQueue != this) ||
      (state.pendingEventCount && state.pendingEventCount != &impl_->count))
    throw std::invalid_argument("Handler already bound to another queue/count");
  state.eventQueue = this;
  state.pendingEventCount = &impl_->count;
}
void CardHandlerEventQueue::unbind(CardHandlerState &state) {
  if (state.eventQueue != this || state.pendingEventCount != &impl_->count)
    throw std::invalid_argument("Handler queue binding mismatch");
  state.eventQueue = nullptr;
  state.pendingEventCount = nullptr;
}
std::uint32_t CardHandlerEventQueue::pending() const {
  return impl_->count.load(std::memory_order_acquire);
}
unsigned CardHandlerEventQueue::queuedNodes() const {
  return impl_->nodes.load(std::memory_order_acquire);
}
void CardHandlerEventQueue::consumeOne(Presonus::NOAA::TCardHandler &handler,
                                       CardHandlerState &state) {
  if (state.eventQueue != this || state.pendingEventCount != &impl_->count)
    throw std::invalid_argument("Handler queue binding mismatch");
  if (!queuedNodes())
    return;
  Core::Threads::ScopedLock main(impl_->mainLock);
  Impl::Slot *slot;
  Core::Threads::ScopedLock queue(impl_->queueLock);
  if (impl_->fifo.isEmpty())
    return;
  slot = impl_->fifo.removeFirst();
  impl_->nodes.fetch_sub(1, std::memory_order_release);
  if (!slot)
    return;
  struct Cleanup {
    Impl &impl;
    Impl::Slot *slot;
    CardHandlerState &state;
    const DeferredRateProjection *rate;
    const DeferredRouteProjection *routes;
    const Core::Property *geq;
    const std::array<unsigned char, 33> *payload;
    ~Cleanup() {
      state.deferredRate = rate;
      state.deferredRoutes = routes;
      state.geqProperty = geq;
      state.geqPayload = payload;
      impl.recycle(slot);
    }
  } cleanup{*impl_,
            slot,
            state,
            state.deferredRate,
            state.deferredRoutes,
            state.geqProperty,
            state.geqPayload};
  auto &event = *slot->event;
  if (event.rate)
    event.rate->property = &event.property;
  if (event.routes)
    event.routes->property = &event.property;
  state.deferredRate = event.rate ? &*event.rate : nullptr;
  state.deferredRoutes = event.routes ? &*event.routes : nullptr;
  state.geqProperty = event.geq ? &event.property : nullptr;
  state.geqPayload = event.geq ? &*event.geq : nullptr;
  handler.setPropertyDeferred(event.property);
}
} // namespace presonus::noaa
