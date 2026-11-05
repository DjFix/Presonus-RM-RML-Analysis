#pragma once
#include "core/public/coreproperty.h"
#include "presonus/noaa/card_handler_state.hpp"
#include <memory>
namespace Presonus::NOAA {
class TCardHandler;
}
namespace presonus::noaa {
// Independent value snapshot, never a native object image. The semantic byte
// count selects the original pool class; sizeof this modern snapshot does not.
struct CardHandlerEvent {
  Core::Property property;
  int semanticBytes;
  std::optional<DeferredRateProjection> rate;
  std::optional<DeferredRouteProjection> routes;
  std::optional<std::array<unsigned char, 33>> geq;
  explicit CardHandlerEvent(const Core::Property &p, int bytes)
      : property(p.type, p.size), semanticBytes(bytes) {}
};
// Source-port FIFO and finite pools. Capacities are explicitly supplied by the
// caller, not inferred historical pool sizes. CCL list owns links only; pool
// slots own snapshots, and the queue owns pool storage. No copying native
// pointers, no arbitrary Property-to-derived cast, and no original setProperty
// implementation is claimed. Caller joins consumer before destroying/unbinding.
class CardHandlerEventQueue {
public:
  CardHandlerEventQueue(unsigned small, unsigned medium, unsigned large);
  ~CardHandlerEventQueue();
  CardHandlerEventQueue(const CardHandlerEventQueue &) = delete;
  CardHandlerEventQueue &operator=(const CardHandlerEventQueue &) = delete;
  // Copies typed values. Projection identity pointers supplied by callers are
  // discarded and rebound to the queue-owned Property only during dispatch.
  bool enqueue(const CardHandlerEvent &);
  void enqueueNull();
  void bind(CardHandlerState &);
  void unbind(CardHandlerState &);
  std::uint32_t pending() const;
  unsigned queuedNodes() const;
  // Removes at most one link, main lock then queue lock. Dispatch/recycle
  // retain both locks as observed natively (Root-scoped correction to sealed
  // contract). On exceptions scope cleanup clears/recycles the consumed event
  // and restores all borrowed projections; exceptions (including cancellation
  // forced unwind) propagate unchanged.
  void consumeOne(Presonus::NOAA::TCardHandler &, CardHandlerState &);

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace presonus::noaa
