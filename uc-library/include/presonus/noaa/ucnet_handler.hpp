#pragma once
#include "presonus/noaa/spi_packets.hpp"
#include "presonus/noaa/ucnet_handler_state.hpp"
#include <memory>
namespace Presonus::NOAA {
// Original RTTI: single ISysexReceiver base. The two tagged constructors are
// independent source-port setup, not recovered original C1/C2 or ARM layout.
class TCardUCNetHandler : public ISysexReceiver {
public:
  TCardUCNetHandler(presonus::noaa::UCNetHandlerSetupTag,
                    presonus::noaa::UCNetHandlerState &state)
      : state_(state) {}
  TCardUCNetHandler(presonus::noaa::UCNetHandlerOwnedSetupTag,
                    Presonus::UC::INetworkManager &network,
                    presonus::dice::ResponseServices &clock,
                    bool createEndpoint = true);
  // Native normal path: unregister, endpoint delete, outgoing then incoming.
  // Lazy singleton construction exceptions retain endpoint, clean both queues,
  // then propagate as in the native application landing path.
  // Host deleting-dtor exception deallocation follows the host C++ ABI; it is
  // outside original native exceptional-path equivalence. Borrowed
  // compatibility mode never owns channel/queues and only touches an existing
  // SPI singleton.
  virtual ~TCardUCNetHandler() noexcept(false);
  TCardUCNetHandler(const TCardUCNetHandler &) = delete;
  TCardUCNetHandler &operator=(const TCardUCNetHandler &) = delete;
  // Independent source-port access, not a recovered original interface.
  presonus::noaa::UCNetHandlerState &portableState() { return state_; }
  Presonus::UC::DiceEndPoint *portableOwnedEndpoint() {
    return owned_ ? owned_->endpoint.get() : nullptr;
  }
  bool accepts(const SysexPacket &) override;
  void receive(const SysexPacket &) override;
  // Original ordinary return declarations unresolved; callback r0 is preserved
  // by these independent int spellings. A manager must already be initialized.
  int startup(int port);
  int shutdown();
  // Provisional ordinary return; original declaration remains unresolved.
  void idleIO();

private:
  std::unique_ptr<presonus::noaa::UCNetHandlerOwnedState> owned_;
  presonus::noaa::UCNetHandlerState &state_;
};
} // namespace Presonus::NOAA
