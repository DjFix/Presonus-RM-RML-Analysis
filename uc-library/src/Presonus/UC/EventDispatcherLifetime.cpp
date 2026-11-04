#include "core/portable/coresingleton.h"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include <stdexcept>

namespace Presonus::UC {
struct EventDispatcher::SourceOwned {
  // Reverse destruction: owning queue flush/list/lock; storage; typed values;
  // IDSet, vectors/hash buckets and dispatcher locks in state.
  presonus::uc::EventDispatcherState state{64};
  presonus::uc::BasicConnectionTypedValues values;
  presonus::uc::BasicQueueStorage storage;
  EventQueue queue;
  SourceOwned()
      : storage(presonus::uc::makeBasicQueueStorage(this, resolve)),
        queue(*storage) {
    state.owningQueue = &queue;
    state.owningStorage = storage.get();
    state.typedContext = this;
    state.typedValue = resolve;
  }
  static void *resolve(void *context, const Event &event,
                       presonus::uc::QueueValueKind kind) {
    auto &self = *static_cast<SourceOwned *>(context);
    return self.values.resolve(event, kind, self.storage->items.value());
  }
};
EventDispatcher::EventDispatcher()
    : owned_(std::make_unique<SourceOwned>()), state_(owned_->state) {}
EventDispatcher::EventDispatcher(presonus::uc::EventDispatcherState &state)
    : state_(state) {}
EventDispatcher::~EventDispatcher() = default;
} // namespace Presonus::UC

DEFINE_STATIC_SINGLETON(Presonus::UC::EventDispatcher)

namespace presonus::uc {
Presonus::UC::EventDispatcher &sourceDispatcherSingleton() {
  return Core::Portable::StaticSingleton<
      Presonus::UC::EventDispatcher>::instance();
}
EventDispatcherState &
DispatcherSourceAccess::state(Presonus::UC::EventDispatcher &dispatcher) {
  return dispatcher.state_;
}
BasicConnectionTypedValues &
DispatcherSourceAccess::values(Presonus::UC::EventDispatcher &dispatcher) {
  if (!dispatcher.owned_)
    throw std::logic_error("owning dispatcher required");
  return dispatcher.owned_->values;
}
OwnedEventQueueState &
DispatcherSourceAccess::storage(Presonus::UC::EventDispatcher &dispatcher) {
  if (!dispatcher.owned_)
    throw std::logic_error("owning dispatcher required");
  return *dispatcher.owned_->storage;
}
} // namespace presonus::uc
