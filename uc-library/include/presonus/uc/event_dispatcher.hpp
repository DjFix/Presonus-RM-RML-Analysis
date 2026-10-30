#pragma once
#include "core/public/corebitset.h"
#include "core/public/corehashmap.h"
#include "core/public/corelinkedlist.h"
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include "presonus/uc/event_queue.hpp"

namespace Presonus::UC {
// Original interface name and single virtual dispatch slot are evidenced by
// the original IEventHandler vtable (12 bytes on ARM: two header words +
// slot0). int is a portable return declaration for observed signed32 results;
// original return spelling/access policy/layout are unencoded. No original
// destructor is recovered. The protected nonvirtual helper does not add a
// virtual slot.
class IEventHandler {
public:
  virtual int handleEvent(void *, const Event &) = 0;

protected:
  ~IEventHandler() = default;
};
} // namespace Presonus::UC
namespace presonus::uc {
enum class DispatcherAudit {
  HandlerLock = 1,
  HandlerUnlock,
  QueueLock,
  QueueUnlock
};
// New source-port state using genuine pinned CCL storage/synchronization.
// Container destruction releases container storage, never EventItems/handlers.
// Caller must drain/resolve owned items. Original ctor/pools/intrusive layout
// and allocation-failure equivalence are not recovered. No concurrent/reentrant
// mutation of handler registrations or external IDs is in the proved domain.
struct EventDispatcherState {
  explicit EventDispatcherState(int modulus = 8);
  EventDispatcherState(const EventDispatcherState &) = delete;
  EventDispatcherState &operator=(const EventDispatcherState &) = delete;
  Core::Threads::Lock handlerLock, queueLock;
  Core::HashMap<int, Presonus::UC::IEventHandler *> handlers;
  Presonus::UC::IEventHandler *fallback = nullptr;
  Core::Vector<int> externalIDs;
  Core::LinkedList<Presonus::UC::EventItem *> queued;
  void *typedContext = nullptr;
  void *(*typedValue)(void *, const Presonus::UC::Event &,
                      QueueValueKind) = nullptr;
  void *auditContext = nullptr;
  void (*audit)(void *,
                DispatcherAudit) = nullptr; // Nonthrowing observation only.
  void observe(DispatcherAudit stage) const;
  Presonus::UC::EventItem *retrieve();

private:
  static int hashIndex(const int &, int);
  Core::Vector<EventQueueNode> nodes_;
  EventQueueState coalescerStorage_;

public:
  Presonus::UC::EventQueue coalescer;
  // Actual pinned CCL allocator; original ctor policy is offset100/delta128.
  Core::IDSet identifiers{100, 128};
};
} // namespace presonus::uc
namespace Presonus::UC {
class EventDispatcher {
public:
  // New preinitialized-state helper, not an original constructor/ARM layout.
  explicit EventDispatcher(presonus::uc::EventDispatcherState &state)
      : state_(state) {}
  static int hashHandlerKey(const int &, int);
  bool updateEvent(const Event &);
  bool hasEvents() const;
  bool isExternalHandler(int);
  // Ordinary return spellings unencoded; observed ID/signed32 and0/1 results.
  int addHandler(IEventHandler *, int flags);
  bool removeHandler(int);
  bool removeHandler(IEventHandler *);
  // These void spellings are compiled/declaration-pending: the original
  // ordinary mangles do not establish return spelling or incidental r0 output.
  void queueEvent(EventItem *);
  void dispatchOne(EventItem *);
  void dispatchAll();

private:
  presonus::uc::EventDispatcherState &state_;
};
} // namespace Presonus::UC
