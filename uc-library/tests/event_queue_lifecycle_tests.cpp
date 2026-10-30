#include "presonus/uc/connection_interfaces.hpp"
#include "presonus/uc/event_queue.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#include <string>
#include <type_traits>
using namespace Presonus::UC;
static_assert(std::is_base_of_v<Core::IntrusiveLink<EventItem>, EventItem>);
static_assert(
    std::is_convertible_v<EventItem *, Core::IntrusiveLink<EventItem> *>);
static_assert(!std::has_virtual_destructor_v<IConnection> &&
              !std::has_virtual_destructor_v<IDataChannel>);
namespace {
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
struct Observation {
  bool active = false, capture = false, held = false;
  pthread_mutex_t *mutex = nullptr;
  unsigned destroyed = 0, selectedFrees = 0;
  std::array<void *, 16> pointers{};
  std::array<bool, 16> freed{};
  std::string trace;
  void event(const std::string &s) {
    if (capture) {
      if (!trace.empty())
        trace += ';';
      trace += s;
    }
  }
  int id(void *p) const {
    for (unsigned i = 0; i < pointers.size(); ++i)
      if (pointers[i] == p)
        return int(i);
    return -1;
  }
} observed;
struct Item final : EventItem {
  unsigned id;
  ParamValueEvent value{};
  explicit Item(unsigned n) : id(n) {
    value.header.type = 20566;
    value.valueBits = n;
  }
  ~Item() override {
    if (observed.capture) {
      require(!observed.held, "payload delete held mutex");
      require(!getNext() && !getPrevious(), "payload still linked on delete");
      observed.event("dtor:" + std::to_string(id));
    }
  }
  Event &getData() override { return value.header; }
};
// Exact base-sized, resource-free concrete context for native ABI variant
// probes. Passing a larger payload-derived allocation to base D0 is invalid
// for GCC's sized delete and was rejected by the preserved first ASan run.
struct BareItem final : EventItem {
  Event &getData() override {
    static Event value;
    return value;
  }
};
static_assert(sizeof(BareItem) == sizeof(EventItem));
void *typed(void *, const Event &event, presonus::uc::QueueValueKind kind) {
  require(kind == presonus::uc::QueueValueKind::Value,
          "wrong typed provider request");
  for (unsigned i = 0; i < observed.pointers.size(); ++i)
    if (observed.pointers[i] && !observed.freed[i]) {
      auto *item = static_cast<Item *>(observed.pointers[i]);
      if (&item->value.header == &event)
        return &item->value;
    }
  throw std::invalid_argument("live bound value required");
}
#include "queue_lifecycle_cases.hpp"
std::string remaining(presonus::uc::OwnedEventQueueState &state) {
  std::string result;
  for (auto *p = state.items.value().getFirst(); p; p = p->getNext()) {
    int id = observed.id(p);
    require(id >= 0, "unbound queued pointer");
    if (!result.empty())
      result += ',';
    result += std::to_string(id);
  }
  return result;
}
} // namespace
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __real_pthread_mutex_lock(pthread_mutex_t *);
extern "C" int __real_pthread_mutex_unlock(pthread_mutex_t *);
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *p,
                                         const pthread_mutexattr_t *a) {
  int result = __real_pthread_mutex_init(p, a);
  if (observed.active) {
    require(!observed.mutex, "unexpected second real mutex");
    require(result == 0, "mutex init failed");
    observed.mutex = p;
  }
  return result;
}
extern "C" int __wrap_pthread_mutex_lock(pthread_mutex_t *p) {
  int result = __real_pthread_mutex_lock(p);
  if (p == observed.mutex) {
    require(!observed.held && result == 0, "mutex lock order failed");
    observed.held = true;
    observed.event("lock");
  }
  return result;
}
extern "C" int __wrap_pthread_mutex_unlock(pthread_mutex_t *p) {
  if (p == observed.mutex) {
    require(observed.held, "mutex unlock order failed");
    observed.held = false;
    observed.event("unlock");
  }
  return __real_pthread_mutex_unlock(p);
}
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *p) {
  if (p == observed.mutex) {
    require(!observed.held, "destroyed held mutex");
    observed.event("mutex_destroy");
    ++observed.destroyed;
    observed.mutex = nullptr;
  }
  int result = __real_pthread_mutex_destroy(p);
  require(result == 0, "real mutex destruction failed");
  return result;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static void observeFree(void *p) {
  int id = observed.id(p);
  if (id >= 0) {
    require(!observed.freed[id], "double delete");
    require(!observed.held, "deallocated under mutex");
    if (observed.capture) {
      ++observed.selectedFrees;
      observed.event("free:" + std::to_string(id));
    }
    observed.freed[id] = true;
    observed.pointers[id] =
        nullptr; // Do not misidentify later allocator address reuse.
  }
}
extern "C" void __wrap__ZdlPv(void *p) {
  observeFree(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  observeFree(p);
  __real__ZdlPvm(p, n);
}
// Explicit native GCC/Itanium variant probes, not portable ABI or ARM claims.
extern "C" void nativeItemD1(EventItem *) asm("_ZN8Presonus2UC9EventItemD1Ev");
extern "C" void nativeItemD0(EventItem *) asm("_ZN8Presonus2UC9EventItemD0Ev");
extern "C" void
nativeQueueD1(EventQueue *) asm("_ZN8Presonus2UC10EventQueueD1Ev");
extern "C" void
nativeQueueD2(EventQueue *) asm("_ZN8Presonus2UC10EventQueueD2Ev");
int main() {
  try {
    unsigned count = 0, totalFrees = 0, totalMutexDestructions = 0;
    for (const auto &test : cases) {
      observed = Observation{};
      const std::string action = test.action;
      for (unsigned i = 0; i < test.count; ++i)
        observed.pointers[i] = action.rfind("item", 0) == 0
                                   ? static_cast<EventItem *>(new BareItem)
                                   : static_cast<EventItem *>(new Item(i));
      presonus::uc::OwnedEventQueueState state(nullptr, typed);
      EventQueue *queue = nullptr;
      bool destroyed = false;
      EventItem *detached = nullptr;
      if (action.rfind("item", 0) != 0) {
        observed.active = true;
        queue = new EventQueue(state);
        require(observed.mutex, "real CCL mutex not initialized");
        std::array<unsigned, 16> order{};
        for (unsigned i = 0; i < test.count; ++i)
          order[i] = i;
        if (test.order == 1)
          for (unsigned i = 0; i < test.count; ++i)
            order[i] = test.count - 1 - i;
        else if (test.order == 2 && test.count)
          for (unsigned i = 0; i < test.count; ++i)
            order[i] = (i + 1) % test.count;
        for (unsigned i = 0; i < test.count; ++i)
          state.append(static_cast<Item *>(observed.pointers[order[i]]));
      }
      observed.capture = true;
      observed.trace.clear();
      int result = 0;
      if (action == "empty")
        result = queue->isEmpty();
      else if (action == "retrieve") {
        detached = queue->retrieveEvent();
        result = detached ? observed.id(detached) : -1;
        require(!detached || (!detached->getNext() && !detached->getPrevious()),
                "retrieve did not detach links");
      } else if (action == "flush")
        queue->flush();
      else if (action == "queueD1") {
        nativeQueueD1(queue);
        destroyed = true;
      } else if (action == "queueD2") {
        nativeQueueD2(queue);
        destroyed = true;
      } else if (action == "itemD1")
        nativeItemD1(static_cast<EventItem *>(observed.pointers[0]));
      else if (action == "itemD0")
        nativeItemD0(static_cast<EventItem *>(observed.pointers[0]));
      else
        throw std::runtime_error("unknown original fixture action");
      if (observed.trace != test.trace) {
        std::cerr << action << " expected " << test.trace << " got "
                  << observed.trace << '\n';
        throw std::runtime_error("original lifecycle trace differs");
      }
      if (action == "empty" || action == "retrieve")
        require(result == test.result, "original method result differs");
      if (queue && !destroyed)
        require(remaining(state) == test.remaining, "remaining FIFO differs");
      if (destroyed)
        require(!state.items && !state.lock && !state.attached &&
                    observed.destroyed == 1,
                "queue deferred CCL teardown to later state lifetime");
      require(!observed.held, "selected method left mutex held");
      totalFrees += observed.selectedFrees;
      totalMutexDestructions += observed.destroyed;
      observed.capture = false;
      if (queue) {
        if (!destroyed)
          queue->~EventQueue();
        ::operator delete(queue);
      }
      for (unsigned i = 0; i < test.count; ++i)
        if (!observed.freed[i]) {
          if (action == "itemD1")
            ::operator delete(observed.pointers[i]);
          else
            delete static_cast<Item *>(observed.pointers[i]);
        }
      require(!observed.mutex, "real mutex lifetime leaked");
      observed.active = false;
      ++count;
    }
    // Same external state is explicitly reattached only after real teardown.
    observed = Observation{};
    observed.active = true;
    presonus::uc::OwnedEventQueueState reusable(nullptr, typed);
    {
      EventQueue q(reusable);
      require(reusable.attached, "first attach failed");
    }
    require(!reusable.lock && !reusable.items && !reusable.attached,
            "first teardown deferred");
    {
      EventQueue q(reusable);
      require(reusable.attached, "reinitialization failed");
    }
    require(observed.destroyed == 2,
            "reinitialized mutex not really destroyed twice");
    observed.active = false;
    std::cout << "PASS original_app_cases=" << count
              << " actual_selected_frees=" << totalFrees
              << " mutex_destroy_at_queue_boundary=" << totalMutexDestructions
              << " real_reinitialization=2\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
