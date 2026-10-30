#include "presonus/dice/uart_assembly.hpp"

namespace Presonus::DICE {
void Dice3Uart::registerReceiver(ISysexReceiver *receiver) {
  Core::Threads::ScopedLock guard(state_.lock);
  state_.receivers.add(receiver);
}

void Dice3Uart::unRegisterReceiver(ISysexReceiver *receiver) {
  Core::Threads::ScopedLock guard(state_.lock);
  state_.receivers.remove(receiver);
}
} // namespace Presonus::DICE
