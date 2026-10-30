#include "presonus/dice/manager.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <stdexcept>

namespace Presonus::DICE {
std::int32_t Dice3Manager::setDiceClockRate(Dice3SampleRate rate) {
  if (!portableSubsystem_)
    throw std::logic_error("Dice3Manager portable runtime is not configured");
  return portableSubsystem_->setRate(rate);
}

std::int32_t Dice3Manager::setDiceClockProfile(Dice3ClockProfile profile) {
  if (!portableSubsystem_)
    throw std::logic_error("Dice3Manager portable runtime is not configured");
  return portableSubsystem_->setClockSource(
      static_cast<Dice3ClockSource>(static_cast<int>(profile) == 1 ? 8 : 24));
}

std::int32_t Dice3Manager::getDice3Info(DiceInfo *info) {
  if (!portableSubsystem_ || !portableServices_ || !info)
    throw std::logic_error(
        "Dice3Manager portable information boundary missing");
  // Division truncates toward zero. Divisor1e6 bounds the quotient enough that
  // adding4000 cannot overflow signed64, even for extreme signed64 raw ticks.
  const auto deadline = portableServices_->clockRawTicks() / 1000000 + 4000;
  while (portableServices_->clockRawTicks() / 1000000 < deadline) {
    if (portableSubsystem_->snapshotPortableState().infoWords[0] != 0xffffffffU)
      break;
    portableServices_->sleepMilliseconds(100);
  }
  const auto state = portableSubsystem_->snapshotPortableState();
  info->portableWords = {state.infoWords[0], state.infoWords[1],
                         state.infoWords[2], state.rateWord, state.clockWord};
  return 0;
}

std::int32_t Dice3Manager::threadEntry() {
  if (!portableUart_ || !portableServices_)
    throw std::logic_error("Dice3Manager portable thread boundary missing");
  while (portableStop_.load(std::memory_order_acquire) == 0) {
    if (portableWorkerMayDispatch())
      portableUart_->onIdle();
    portableServices_->sleepMilliseconds(1);
  }
  return 0;
}

void Dice3Manager::release() {
  portableStop_.store(1, std::memory_order_release);
  if (!portableServices_)
    throw std::logic_error("Dice3Manager portable thread boundary missing");
  portableServices_->terminateThread();
}
} // namespace Presonus::DICE
