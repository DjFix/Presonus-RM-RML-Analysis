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
} // namespace Presonus::UC
