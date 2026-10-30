#pragma once
#include "presonus/noaa/spi_packets.hpp"
#include "presonus/noaa/ucnet_handler_state.hpp"
namespace Presonus::NOAA {
// Original RTTI: single ISysexReceiver base. Source-port setup does not perform
// original C1/C2 SPI registration, own queues, or claim original ABI/lifecycle.
class TCardUCNetHandler : public ISysexReceiver {
public:
  TCardUCNetHandler(presonus::noaa::UCNetHandlerSetupTag,
                    presonus::noaa::UCNetHandlerState &state)
      : state_(state) {}
  bool accepts(const SysexPacket &) override;
  void receive(const SysexPacket &) override;
  // Original ordinary return declarations unresolved; callback r0 is preserved
  // by these independent int spellings. A manager must already be initialized.
  int startup(int port);
  int shutdown();

private:
  presonus::noaa::UCNetHandlerState &state_;
};
} // namespace Presonus::NOAA
