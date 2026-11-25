#include "../../network_next_services/fixture_next_manager.hpp"
#include "presonus/uc/adapter_handler.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
AdapterHandlerState *active;
Core::Threads::Lock *trackedLock;
std::ostringstream trace;
bool locked;
} // namespace

extern "C" void
__real__ZN4Core8Platform9PosixLock4lockEv(Core::Threads::Lock *);
extern "C" void
__real__ZN4Core8Platform9PosixLock6unlockEv(Core::Threads::Lock *);
extern "C" void __real__ZN8Presonus2UC14AdapterHandler21invalidateAddressListEv(
    AdapterHandler *);

extern "C" void
__wrap__ZN4Core8Platform9PosixLock4lockEv(Core::Threads::Lock *lock) {
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (lock == trackedLock) {
    locked = true;
    trace << " lock:" << unsigned(active->suspended) << ':'
          << unsigned(active->cacheValid);
  }
}

extern "C" void
__wrap__ZN4Core8Platform9PosixLock6unlockEv(Core::Threads::Lock *lock) {
  if (lock == trackedLock) {
    trace << " unlock:" << unsigned(active->suspended) << ':'
          << unsigned(active->cacheValid);
    locked = false;
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
}

extern "C" void __wrap__ZN8Presonus2UC14AdapterHandler21invalidateAddressListEv(
    AdapterHandler *adapter) {
  if (!locked || &adapter->sourcePortState() != active)
    std::abort();
  trace << " invalidate:" << unsigned(active->suspended) << ':'
        << unsigned(active->cacheValid);
  __real__ZN8Presonus2UC14AdapterHandler21invalidateAddressListEv(adapter);
}

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  EventDispatcher dispatcher;
  EventFactory factory;
  NetworkManagerState state{dispatcher, factory};
  FixtureNextManager manager(state);
  CclAdapterServices services;
  AdapterHandlerState adapterState(services);
  AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
  adapterState.suspended = std::atoi(argv[1]);
  adapterState.cacheValid = std::atoi(argv[3]);
  adapterState.changed = 17;
  state.adapterHandler = &adapter;
  state.multicastReceiverEnabled = true;
  state.waitingForOutgoingEvents = 37;
  active = &adapterState;
  trackedLock = manager.getLock();
  const int result =
      manager.NetworkManager::suspendNetworkAdapters(std::atoi(argv[2]));
  trackedLock = nullptr;
  active = nullptr;
  if (locked || !state.multicastReceiverEnabled ||
      state.waitingForOutgoingEvents != 37 || adapterState.changed != 17)
    return 3;
  std::cout << result << ' ' << unsigned(adapterState.suspended) << ' '
            << unsigned(adapterState.cacheValid) << trace.str() << '\n';
}
