#include "presonus/noaa/card.hpp"
#include <limits>
namespace presonus::noaa {
void CclCardResponseRuntime::onIdle(bool force) {
  Presonus::NOAA::TCardSPI::instance().onIdle(force);
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
TCard::TCard()
    : ownedRuntime_(std::in_place), ownedState_(std::in_place),
      state_(*ownedState_),
      diagnostics_(presonus::noaa::spiServiceConstructionIO()) {
  // Logical state, never an ARM byte-layout model. Value initialization zeros
  // owned application fields; original unspecified bytes have no host analogue.
  state_.observedWord10 = state_.observedWord14 =
      std::numeric_limits<std::uint32_t>::max();
  setPortableResponseServices(ownedRuntime_->response());
  TCardSPI::instance().registerReceiver(this);
  registered_ = true;
}
TCard::~TCard() {
  if (registered_)
    // Retain original lazy singleton behavior even after an external reset.
    TCardSPI::instance().unRegisterReceiver(this);
}
} // namespace Presonus::NOAA
