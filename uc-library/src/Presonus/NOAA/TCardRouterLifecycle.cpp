#include "presonus/noaa/router.hpp"
#include <array>

namespace presonus::noaa {
void CclRouterResponseRuntime::onIdle(bool force) {
  Presonus::NOAA::TCardSPI::instance().onIdle(force);
}
} // namespace presonus::noaa

namespace Presonus::NOAA {
TCardRouter::TCardRouter()
    : ownedRuntime_(std::in_place),
      ownedState_(std::in_place, std::array<unsigned char, 2312>{}),
      state_(*ownedState_),
      diagnostics_(presonus::noaa::spiServiceConstructionIO()),
      lookup_(presonus::noaa::rm13731LinkAddressRouterLookup()) {
  // Exact original known defaults: base response fields, null table views,
  // pending flag/count, and512four-byte queued route entries. The original
  // command prefix[0x18,0x118) was untouched; modern owned storage additionally
  // clears that unspecified prefix as an explicit source-port choice, never
  // claimed as recovered original initialization/layout behavior.
  setPortableResponseServices(ownedRuntime_->response());
  TCardSPI::instance().registerReceiver(this);
  registered_ = true;
}
TCardRouter::~TCardRouter() noexcept(false) {
  if (registered_)
    // Original D1/D2 also lazily instantiate SPI if its global is now null.
    TCardSPI::instance().unRegisterReceiver(this);
  // Owned actual CCL state/lock destruction follows, after unregister. The
  // independent borrowed overload owns no registration or external state.
}
} // namespace Presonus::NOAA
