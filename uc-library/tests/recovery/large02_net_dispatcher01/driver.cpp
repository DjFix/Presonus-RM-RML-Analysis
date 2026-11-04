#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>
using namespace Presonus::UC;
using namespace presonus::uc;
namespace {
struct Allocation {
  void *p;
  size_t size;
  int label;
};
Allocation allocations[1024];
int allocCount = 0, phase = 0, count = 0;
int trace[4096], traceCount = 0;
int syncTrace[256], syncCount = 0;
bool queueHeld = false;
void *object = nullptr;
void *itemPointers[64]{};
void *mutexes[16];
int mutexCount = 0;
void observe(int label) {
  if (phase == 3)
    trace[traceCount++] = label;
}
void released(void *p) {
  if (!p)
    return;
  if (p == object)
    observe(900);
  for (int i = 0; i < count; ++i)
    if (p == itemPointers[i])
      observe(200 + i);
  for (int i = 0; i < allocCount; ++i)
    if (allocations[i].p == p) {
      observe(allocations[i].label);
      allocations[i].p = nullptr;
      return;
    }
}
struct Handler : IEventHandler {
  int handleEvent(void *, const Event &) override { return 0; }
};
struct Item : TypedEventItem<ParamValueEvent> {
  int id;
  explicit Item(int n) : id(n) {
    value.header.type = 20566;
    std::strcpy(value.path.data(), "test");
  }
  ~Item() override {
    if (queueHeld)
      std::abort();
    observe(100 + id);
  }
};
} // namespace
extern "C" void *__real__Znam(size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, size_t);
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __real_pthread_mutex_lock(pthread_mutex_t *);
extern "C" int __real_pthread_mutex_unlock(pthread_mutex_t *);
extern "C" void *__wrap__Znam(size_t n) {
  void *p = __real__Znam(n);
  if (phase == 1 || phase >= 20) {
    const int label = phase == 1 ? 1001 + allocCount : phase;
    allocations[allocCount++] = {p, n, label};
  }
  return p;
}
extern "C" void __wrap__ZdaPv(void *p) {
  released(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, size_t n) {
  released(p);
  __real__ZdaPvm(p, n);
}
extern "C" void __wrap__ZdlPv(void *p) {
  released(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, size_t n) {
  released(p);
  __real__ZdlPvm(p, n);
}
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *p,
                                         const pthread_mutexattr_t *a) {
  if (phase == 1)
    mutexes[mutexCount++] = p;
  return __real_pthread_mutex_init(p, a);
}
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *p) {
  for (int i = 0; i < mutexCount; ++i)
    if (mutexes[i] == p)
      observe(700 + i);
  return __real_pthread_mutex_destroy(p);
}
extern "C" int __wrap_pthread_mutex_lock(pthread_mutex_t *p) {
  int result = __real_pthread_mutex_lock(p);
  if (phase == 3 && p == mutexes[2]) {
    if (result || queueHeld)
      std::abort();
    queueHeld = true;
    syncTrace[syncCount++] = 1;
  }
  return result;
}
extern "C" int __wrap_pthread_mutex_unlock(pthread_mutex_t *p) {
  int result = __real_pthread_mutex_unlock(p);
  if (phase == 3 && p == mutexes[2]) {
    if (result || !queueHeld)
      std::abort();
    queueHeld = false;
    syncTrace[syncCount++] = 2;
  }
  return result;
}
int main(int argc, char **argv) {
  if (argc > 1 && !std::strcmp(argv[1], "--source-contracts")) {
    auto &a = sourceDispatcherSingleton();
    auto &b = sourceDispatcherSingleton();
    if (&a != &b || a.hasEvents() ||
        !DispatcherSourceAccess::state(a).typedValue)
      return 10;
    {
      EventDispatcherState state;
      auto *item = new Item(0);
      {
        EventDispatcher borrowed(state);
        borrowed.queueEvent(item);
      }
      if (state.queued.isEmpty() || state.retrieve() != item)
        return 11;
      delete item;
    }
    {
      EventDispatcher active;
      Handler handler;
      int id = active.addHandler(&handler, 1);
      if (id != 100 || !active.isExternalHandler(id))
        return 12;
      auto *item = new Item(0);
      item->value.header.routeB = static_cast<unsigned>(id);
      active.queueEvent(item);
      active.dispatchAll();
      if (active.hasEvents() || !active.removeHandler(id) ||
          active.isExternalHandler(id))
        return 13;
    }
    std::puts("{\"singleton_owned\":true,\"borrowed_preserved\":true,"
              "\"registration_dispatch\":true}");
    return 0;
  }
  count = argc > 1 ? std::atoi(argv[1]) : 0;
  if (count < 0 || count > 64)
    return 20;
  phase = 1;
  auto *d = new EventDispatcher;
  object = d;
  phase = 0;
  auto &s = DispatcherSourceAccess::state(*d);
  if (!s.typedValue || !s.owningStorage || !s.owningQueue ||
      !s.queued.isEmpty())
    return 2;
  int id = s.identifiers.newID();
  Handler handler;
  phase = 600;
  s.externalIDs.add(12);
  phase = 801;
  s.handlers.add(1, &handler);
  phase = 863;
  s.handlers.add(63, &handler);
  phase = 0;
  for (int i = 0; i < count; ++i) {
    auto *item = new Item(i);
    itemPointers[i] = item;
    d->queueEvent(item);
  }
  bool before = d->hasEvents();
  // Resolve a genuine external typed payload and the live queued typed value.
  bool updated = false;
  if (count) {
    ParamValueEvent incoming;
    incoming.header.type = 20566;
    std::strcpy(incoming.path.data(), "test");
    incoming.valueBits = 123;
    auto binding = DispatcherSourceAccess::values(*d).bind(incoming);
    updated = d->updateEvent(incoming.header);
    auto *first = dynamic_cast<Item *>(
        DispatcherSourceAccess::storage(*d).items->getFirst());
    if (!first || first->value.valueBits != 123)
      return 3;
  }
  phase = 3;
  delete d;
  phase = 0;
  std::printf("{\"buckets\":%zu,\"id\":%d,\"before\":%s,\"updated\":%s,"
              "\"allocations\":[",
              allocations[0].size /
                  sizeof(Core::HashMap<int, IEventHandler *>::TList),
              id, before ? "true" : "false", updated ? "true" : "false");
  for (int i = 0; i < allocCount; ++i)
    std::printf("%s[%zu,%d]", i ? "," : "", allocations[i].size,
                allocations[i].label);
  std::printf("],\"trace\":[");
  for (int i = 0; i < traceCount; ++i)
    std::printf("%s%d", i ? "," : "", trace[i]);
  std::printf("],\"queue_sync\":[");
  for (int i = 0; i < syncCount; ++i)
    std::printf("%s%d", i ? "," : "", syncTrace[i]);
  std::puts("]}");
  return 0;
}
