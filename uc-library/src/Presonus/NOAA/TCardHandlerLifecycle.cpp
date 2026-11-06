#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include "presonus/noaa/router.hpp"
#include <new>
namespace Presonus::NOAA {
struct TCardHandler::Owned {
  template <class T> static T *constructDependency() {
    void *storage = ::operator new(sizeof(T));
    try {
      return ::new (storage) T;
    } catch (...) {
      // Native new-expression failure frees only the unconstructed storage.
      // Earlier completed dependencies remain registered and are not destroyed.
      ::operator delete(storage);
      throw;
    }
  }
  // Explicit source-port capacities, not inferred original pool cardinalities.
  // Both real CCL locks and FIFO precede the dependent Card/Router lifetimes.
  presonus::noaa::CardHandlerEventQueue queue{64, 64, 64};
  presonus::noaa::CclCardResponseRuntime runtime;
  // Original successful raw dependency allocations remain registered if a
  // later constructor stage throws. Do not replace this application retention
  // with unique_ptr member unwinding; the successful Handler owns deletion.
  TCard *card = constructDependency<TCard>();
  TCardRouter *router = constructDependency<TCardRouter>();
  presonus::noaa::CardHandlerState state{*card};
  Owned() {
    state.router = router;
    queue.bind(state);
  }
};
TCardHandler::TCardHandler()
    : Core::Threads::Thread("NOAA Handler source port"),
      owned_(std::make_unique<Owned>()), state_(owned_->state) {
  setPortableResponseServices(owned_->runtime.response());
  TCardSPI::instance().registerReceiver(this);
  registered_ = true;
  setPriority(4);
}
TCardHandler::TCardHandler(presonus::noaa::CardHandlerSetupTag,
                           presonus::noaa::CardHandlerState &state,
                           presonus::dice::ResponseServices &response)
    : Core::Threads::Thread("NOAA Handler source port"), state_(state) {
  setPortableResponseServices(response);
}
TCardHandler::~TCardHandler() {
  // Modern POSIX terminate on an unstarted thread is invalid. The guard and
  // join are explicit source-port safety adaptations, not legacy behavior.
  if (started_) {
    Core::Threads::Thread::terminate();
    join(3000);
  }
  if (registered_)
    TCardSPI::instance().unRegisterReceiver(this);
  if (owned_) {
    // Preserve Card deleting destruction before Router D1 and deallocation,
    // followed by FIFO links/pool reclamation and queue/main lock destruction.
    delete owned_->card;
    owned_->card = nullptr;
    // Original calls Router D1 and only then operator delete. A C++ delete
    // expression would additionally free storage if D1 throws, which differs.
    owned_->router->~TCardRouter();
    ::operator delete(owned_->router);
    owned_->router = nullptr;
    owned_.reset();
  }
}
} // namespace Presonus::NOAA
