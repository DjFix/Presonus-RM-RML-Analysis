#include "presonus/uc/network_manager_services.hpp"
#include "presonus/uc/server_registrar.hpp"

namespace Presonus::UC {
int NetworkManager::registerListener(INetworkListener *listener) {
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  if (state_.startedCount <= 0)
    return 1001;
  if (!state_.registrar->hasListeners())
    state_.discovery->startListening();
  state_.registrar->addListener(listener);
  return 0;
}

int NetworkManager::unregisterListener(INetworkListener *listener) {
  Core::Threads::ScopedLock guard(state_.errorReporterLock);
  if (state_.startedCount <= 0)
    return 1001;
  state_.registrar->removeListener(listener);
  if (!state_.registrar->hasListeners())
    state_.discovery->stopListening();
  return 0;
}
} // namespace Presonus::UC
