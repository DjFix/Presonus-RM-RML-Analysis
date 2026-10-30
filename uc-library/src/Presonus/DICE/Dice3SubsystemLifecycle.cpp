#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
namespace Presonus::DICE {
Dice3Subsystem::Dice3Subsystem()
    : runtime_(&presonus::dice::requireSubsystemRuntime()) {
  state_.infoWords = {0xffffffffU, 0xffffffffU, 0};
  state_.rateWord = 1;
  state_.clockWord = 24;
  auto &uart = Dice3Uart::instance();
  runtime_->bind(*this, uart);
  uart.registerReceiver(this);
  resetDice3();
}
// Original D1/D2 do not unregister or own the UART; preserve that lifecycle.
Dice3Subsystem::~Dice3Subsystem() {}
} // namespace Presonus::DICE
