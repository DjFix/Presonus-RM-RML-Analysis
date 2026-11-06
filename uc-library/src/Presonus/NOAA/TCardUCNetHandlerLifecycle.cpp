#include "presonus/noaa/ucnet_handler.hpp"

namespace presonus::noaa {
UCNetHandlerOwnedState::UCNetHandlerOwnedState(
    Presonus::UC::INetworkManager &network,
    presonus::dice::ResponseServices &clock, bool createEndpoint)
    : endpoint(createEndpoint ? std::make_unique<Presonus::UC::DiceEndPoint>(
                                    incoming, outgoing)
                              : nullptr),
      channel(endpoint ? std::optional<presonus::noaa::UCNetEndpointChannel>(
                             std::in_place, *endpoint, incoming)
                       : std::nullopt),
      view{incoming, network, clock, nullptr,   channel ? &*channel : nullptr,
           0,        0,       0,     &outgoing, 0} {}
} // namespace presonus::noaa

namespace Presonus::NOAA {
TCardUCNetHandler::TCardUCNetHandler(presonus::noaa::UCNetHandlerOwnedSetupTag,
                                     Presonus::UC::INetworkManager &network,
                                     presonus::dice::ResponseServices &clock,
                                     bool createEndpoint)
    : owned_(std::make_unique<presonus::noaa::UCNetHandlerOwnedState>(
          network, clock, createEndpoint)),
      state_(owned_->view) {}

TCardUCNetHandler::~TCardUCNetHandler() noexcept(false) {
  if (owned_) {
    // Real CCL Singleton provider includes the original lazy creation path.
    // The native exceptional path skips endpoint deletion but destroys both
    // queues. Preserve that application behavior, including its retained
    // endpoint, rather than silently substituting stronger RAII cleanup.
    try {
      TCardSPI::instance().unRegisterReceiver(this);
    } catch (...) {
      owned_->endpoint.release();
      throw;
    }
  } else if (auto *spi = presonus::noaa::SpiServiceAccess::singleton()) {
    // Explicit borrowed compatibility mode is outside original equivalence:
    // never create a hardware service merely to destroy a borrowed view.
    spi->unRegisterReceiver(this);
  }
  // owned_ performs actual endpoint deletion, then outgoing/incoming queue
  // destructors. Compiler D0 deletes this; D1/D2 do not. No synthetic events.
}
} // namespace Presonus::NOAA
