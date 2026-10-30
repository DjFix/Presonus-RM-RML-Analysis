#include "../../portable/dice/ManagerWorkerGuard.hpp"
#include "presonus/dice/manager.hpp"
#include "presonus/dice/manager_lifetime.hpp"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"

DEFINE_SINGLETON(Presonus::DICE::Dice3Manager)

namespace Presonus::DICE {
Dice3Manager::Dice3Manager() : portableSink_(nullptr) {
  portableReceiverReady_.store(false, std::memory_order_relaxed);
  portableOwner_ = presonus::dice::makeConfiguredManagerRuntime(*this);
  portableServices_ = &portableOwner_->managerServices();
  auto &uart = Dice3Uart::instance();
  portableUart_ = &uart;
  {
    auto &state = presonus::dice::UartLifetimeAccess::state(uart);
    Core::Threads::ScopedLock guard(state.lock);
    portableReceiverBaseline_ = state.receivers.count();
  }
  ownedWorker_ = std::make_unique<presonus::dice::ManagerWorkerGuard>(*this);
  presonus::panel::UartCommAccess::ownedServices(
      uart, portableOwner_->uartServices());
  // Preserve original virtual open, ignored result, start, child publication.
  auto &port = static_cast<Presonus::Panel::IPanelIO &>(uart);
  port.open("/dev/ttyS0");
  ownedWorker_->requestStart();
  Core::Threads::Thread::start();
  {
    presonus::dice::ScopedSubsystemRuntime scope(
        portableOwner_->subsystemRuntime());
    ownedSubsystem_ = std::make_unique<Dice3Subsystem>();
  }
  portableSubsystem_ = ownedSubsystem_.get();
  portableOwner_->bindChild(*portableSubsystem_);
  portableSink_ = &portableOwner_->routeSink();
  portableProgrammerServices_ = &portableOwner_->programmerServices();
  portableReceiverReady_.store(true, std::memory_order_release);
}
Dice3Manager::Dice3Manager(presonus::dice::RouteSink &sink)
    : portableSink_(&sink) {}
void Dice3Manager::retirePortableReceiver() {
  if (portableReceiverDetached_ || !portableUart_)
    return;
  if (ownedSubsystem_) {
    portableUart_->unRegisterReceiver(ownedSubsystem_.get());
  } else {
    // Constructor rollback: no external dispatch/publication is permitted yet.
    // Remove pointers added after our baseline without dereferencing a failed
    // constructor object. The real registration API takes its own UART lock.
    auto &state = presonus::dice::UartLifetimeAccess::state(*portableUart_);
    for (;;) {
      ISysexReceiver *receiver = nullptr;
      {
        Core::Threads::ScopedLock guard(state.lock);
        if (state.receivers.count() <= portableReceiverBaseline_)
          break;
        receiver = state.receivers.at(state.receivers.count() - 1);
      }
      portableUart_->unRegisterReceiver(receiver);
    }
  }
  portableReceiverDetached_ = true;
}
Dice3Manager::~Dice3Manager() {
  // Explicit modern-source adaptation: CCL Thread destruction itself does not
  // join. Quiesce before owned child deletion; failed construction is covered
  // by the last-declared guard member as well.
  if (ownedWorker_)
    ownedWorker_->quiesce();
  ownedSubsystem_.reset();
}
} // namespace Presonus::DICE
