#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/uc/adapter_handler.hpp"
#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/multicast_connection.hpp"
#include "presonus/uc/network_manager_services.hpp"

namespace Presonus::UC {
Core::Threads::Lock *NetworkManager::getLock() {
  return &state_.errorReporterLock;
}

bool NetworkManager::isStarted() const { return state_.startedCount > 0; }

int NetworkManager::addErrorReporter(INetworkErrorReporter *reporter) {
  if (!reporter)
    return 101;
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  state_.errorReporters.append(reporter);
  return 0;
}

int NetworkManager::removeErrorReporter(INetworkErrorReporter *reporter) {
  if (!reporter)
    return 101;
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  return state_.errorReporters.remove(reporter) ? 0 : 100;
}
void NetworkManager::enableMulticastReceiver(bool enabled) {
  if (state_.multicastReceiverEnabled == enabled)
    return;
  state_.multicastReceiverEnabled = enabled;
  auto *connection = state_.connectionHandler->getMulticastConnection();
  if (enabled)
    connection->addReceiver(this);
  else
    connection->removeReceiver(this);
}

int NetworkManager::suspendNetworkAdapters(unsigned char requested) {
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  auto &adapter = *state_.adapterHandler;
  auto &suspended = adapter.sourcePortState().suspended;
  const std::uint8_t normalized = requested != 0;
  if (suspended != normalized) {
    suspended = normalized;
    adapter.invalidateAddressList();
  }
  return 0;
}

int NetworkManager::waitForOutgoingEvents(int timeout) {
  struct RestoreFlag {
    std::uint8_t &flag;
    std::uint8_t saved;
    ~RestoreFlag() { flag = saved; }
  };
  const RestoreFlag restore{state_.waitingForOutgoingEvents,
                            state_.waitingForOutgoingEvents};
  state_.waitingForOutgoingEvents = 1;
  const auto deadline = Core::SystemClock::getMilliseconds() + timeout;
  while (hasOutgoingEvents()) {
    Core::Threads::CurrentThread::sleep(10);
    if (Core::SystemClock::getMilliseconds() >= deadline)
      break;
  }
  return 0;
}
} // namespace Presonus::UC
