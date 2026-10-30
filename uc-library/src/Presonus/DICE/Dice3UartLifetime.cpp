#include "presonus/dice/uart_assembly.hpp"
#include "presonus/dice/uart_packet_log.hpp"

namespace presonus::dice {
// Independent owned source-port storage. CCL supplies every buffer/vector/lock;
// inactive receive bytes are initialized safely, not claimed as original data.
struct UartOwnedState {
  UartAssemblyState state{std::array<unsigned char, 67>{}, 0, 0};
  CclPacketLogSink sink;
  CclAssemblyCallbacks callbacks{sink};
};
} // namespace presonus::dice

namespace Presonus::DICE {
Dice3Uart::Dice3Uart()
    : owned_(std::make_unique<presonus::dice::UartOwnedState>()),
      state_(owned_->state), callbacks_(owned_->callbacks) {}

Dice3Uart::Dice3Uart(presonus::dice::UartAssemblyState &state,
                     presonus::dice::AssemblyCallbacks &callbacks)
    : state_(state), callbacks_(callbacks) {}

Dice3Uart::~Dice3Uart() {
  // This is the original derived pre-close, distinct from the unconditional
  // later real UARTComm base-destructor close. Member RAII cleans owned state
  // after this guard ends, before base UART/Singleton teardown.
  Core::Threads::ScopedLock guard(state_.lock);
  if (closeGateBits_ != 0xffffffffu)
    Presonus::Panel::UARTComm::close();
  closeGateBits_ = 0xffffffffu;
}
} // namespace Presonus::DICE
