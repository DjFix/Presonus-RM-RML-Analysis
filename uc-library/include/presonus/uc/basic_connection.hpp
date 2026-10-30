#pragma once
#include "presonus/uc/connection_interfaces.hpp"
#include "presonus/uc/event_queue.hpp"
#include <memory>
namespace presonus::uc {
struct BasicConnectionProviders;
struct BasicConnectionSourceAccess;
// Independent composition of already initialized providers. append transfers
// the live item to caller-managed queue storage and must succeed synchronously
// without throwing. Input and queued typed payloads must be disjoint.
// Original static factory initialization, addEvent declaration/ABI, pools and
// BasicConnection construction/destruction remain pending.
struct BasicConnectionState {
  Presonus::UC::EventQueue *queue = nullptr;
  Presonus::UC::EventFactory *factory = nullptr;
  EventQueueState *storage = nullptr;
  void *context = nullptr;
  void (*append)(void *, Presonus::UC::EventItem *) = nullptr;
};
} // namespace presonus::uc
namespace Presonus::UC {
class NetworkActivityManager;
class BasicConnection : public IConnection {
public:
  // Independent borrowed-source constructor, outside original lifecycle scope.
  explicit BasicConnection(presonus::uc::BasicConnectionState &state);
  // Original parameter identity retained. Requires explicit real
  // source-provider scope; original factory/global initialization is not
  // silently fabricated.
  explicit BasicConnection(int);
  bool sendEvent(const Event &) override;
  // A nonnull opaque pointer must identify a live EventItem eligible for
  // virtual delete. Coalescing destroys that incoming item; a miss transfers
  // it to append. The portable implementation uses actual virtual delete,
  // without claiming the original pool/destructor-variant ABI.
  bool queueEvent(void *) override;
  virtual ~BasicConnection();
  bool hasQueuedEvents() const;

private:
  friend struct presonus::uc::BasicConnectionSourceAccess;
  struct SourceOwned;
  BasicConnection(int, const presonus::uc::BasicConnectionProviders &);
  int connectionType_ = 0;
  NetworkActivityManager *activity_ = nullptr;
  std::unique_ptr<SourceOwned> owned_;
  presonus::uc::BasicConnectionState &state_;
};
} // namespace Presonus::UC
