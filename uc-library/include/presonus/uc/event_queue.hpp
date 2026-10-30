#pragma once
#include "core/system/corethread.h"
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/misc_events.hpp"
#include "presonus/uc/parameter_events.hpp"
#include <optional>

namespace presonus::uc {
struct OwnedEventQueueState;
enum class QueueValueKind {
  Value,
  Increment,
  Color,
  String,
  StringList,
  Range,
  FileRate,
  TimeCode
};
// Independent existing-item list and typed-view bridge. No original Core list,
// lock, allocator, ownership or object layout is implemented here. Callbacks
// must not mutate topology and must return the existing live typed storage.
// lock/unlock callbacks must exist, succeed and not throw. Payload/getData
// callbacks may unwind through the portable RAII guard; original ARM exception
// unwinding is not claimed validated. All string buffers must contain a NUL.
struct EventQueueNode {
  Presonus::UC::EventItem *item = nullptr;
  EventQueueNode *next = nullptr;
};
struct EventQueueState {
  EventQueueNode *head = nullptr;
  void *context = nullptr;
  void (*lock)(void *) = nullptr;
  void (*unlock)(void *) = nullptr;
  void *(*value)(void *, const Presonus::UC::Event &, QueueValueKind) = nullptr;
  OwnedEventQueueState *owned = nullptr;
};
// Independent source-owned queue initialization. The actual typed provider
// must resolve live values without tag-only casts and outlive queue callbacks.
// Caller serializes lifetime: this state outlives its EventQueue; queued items
// are uniquely owned, valid heap EventItems, in no other intrusive list.
// Only one queue facade attaches at a time. Queue destruction flushes, destroys
// the actual CCL list, then destroys the actual CCL mutex before returning.
// Later explicit queue construction reinitializes both; no cleanup is deferred
// to this independent state object's eventual destruction.
struct OwnedEventQueueState {
  using ValueProvider = void *(*)(void *, const Presonus::UC::Event &,
                                  QueueValueKind);
  std::optional<Core::Threads::Lock> lock;
  std::optional<Core::IntrusiveLinkedList<Presonus::UC::EventItem>> items;
  bool attached = false;
  EventQueueState view;
  void *typedContext;
  ValueProvider typedValue;
  OwnedEventQueueState(void *, ValueProvider);
  OwnedEventQueueState(const OwnedEventQueueState &) = delete;
  OwnedEventQueueState &operator=(const OwnedEventQueueState &) = delete;
  // Independent ownership transfer, not a recovered original method.
  void append(Presonus::UC::EventItem *);
  void attach();
};
} // namespace presonus::uc
namespace Presonus::UC {
class EventQueue {
public:
  // Existing borrowed-state constructor retains its nonowning source lifetime;
  // original queue destructor behavior is recovered only for Owned state.
  // Both constructors are independent source APIs, not original ARM layout.
  explicit EventQueue(presonus::uc::EventQueueState &state) : state_(state) {}
  explicit EventQueue(presonus::uc::OwnedEventQueueState &state)
      : state_(state.view) {
    state.attach();
  }
  ~EventQueue();
  // These ordinary return declarations remain unencoded/provisional.
  EventItem *retrieveEvent();
  bool isEmpty() const;
  void flush();
  template <class T> bool update(const Event &);
  bool updateEvent(const Event &);

private:
  presonus::uc::EventQueueState &state_;
};
extern template bool EventQueue::update<ParamValueEvent>(const Event &);
extern template bool EventQueue::update<ParamIncrementEvent>(const Event &);
extern template bool EventQueue::update<ParamColorEvent>(const Event &);
extern template bool EventQueue::update<ParamStringEvent>(const Event &);
extern template bool EventQueue::update<ParamStringListEvent>(const Event &);
extern template bool EventQueue::update<ParamRangeEvent>(const Event &);
extern template bool EventQueue::update<FileDataRateEvent>(const Event &);
extern template bool EventQueue::update<TimeCodeEvent>(const Event &);
} // namespace Presonus::UC
