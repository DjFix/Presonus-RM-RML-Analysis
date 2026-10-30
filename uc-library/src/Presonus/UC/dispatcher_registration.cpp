#include "presonus/uc/event_dispatcher.hpp"

namespace Presonus::UC {
int EventDispatcher::addHandler(IEventHandler *handler, int flags) {
  Core::Threads::ScopedLock guard(state_.handlerLock);
  state_.observe(presonus::uc::DispatcherAudit::HandlerLock);
  const int id = state_.identifiers.newID();
  state_.handlers.add(id, handler);
  if (flags & 1)
    state_.externalIDs.add(id);
  state_.observe(presonus::uc::DispatcherAudit::HandlerUnlock);
  return id;
}
bool EventDispatcher::removeHandler(int id) {
  Core::Threads::ScopedLock guard(state_.handlerLock);
  state_.observe(presonus::uc::DispatcherAudit::HandlerLock);
  state_.identifiers.releaseID(id);
  state_.externalIDs.remove(id);
  const bool removed = state_.handlers.remove(id);
  state_.observe(presonus::uc::DispatcherAudit::HandlerUnlock);
  return removed;
}
bool EventDispatcher::removeHandler(IEventHandler *handler) {
  Core::Threads::ScopedLock guard(state_.handlerLock);
  state_.observe(presonus::uc::DispatcherAudit::HandlerLock);
  int id = 0;
  const bool found = state_.handlers.getKey(id, handler);
  // The nested call intentionally recursively locks the genuine CCL mutex.
  const bool removed = found ? removeHandler(id) : false;
  state_.observe(presonus::uc::DispatcherAudit::HandlerUnlock);
  return removed;
}
} // namespace Presonus::UC
