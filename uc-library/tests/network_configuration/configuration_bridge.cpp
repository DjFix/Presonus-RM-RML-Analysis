#include "fixture_configuration_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

namespace {
std::string trace;
bool capture = false;
int lockDepth = 0;
Core::Threads::Lock *expectedLock = nullptr;
void *observedLock = nullptr;
void check(bool value) {
  if (!value)
    std::abort();
}
std::int32_t signedWord(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
struct UnstartedThread final : Core::Threads::Thread {
  UnstartedThread() : Thread("network-configuration-proof-unstarted") {}
  int threadEntry() override { std::abort(); }
};
void observeLock(void *address) {
  const auto p = reinterpret_cast<std::uintptr_t>(address);
  const auto start = reinterpret_cast<std::uintptr_t>(expectedLock);
  check(expectedLock && p >= start && p < start + sizeof(*expectedLock));
  if (!observedLock)
    observedLock = address;
  check(observedLock == address);
}
} // namespace
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __real__ZN4Core8Platform11PosixThread11setPriorityEi(void *,
                                                                     int);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *lock) {
  if (capture) {
    observeLock(lock);
    check(lockDepth == 0);
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (capture) {
    lockDepth = 1;
    trace += "L;";
  }
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *lock) {
  if (capture) {
    observeLock(lock);
    check(lockDepth == 1);
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
  if (capture) {
    lockDepth = 0;
    trace += "U;";
  }
}
extern "C" void
__wrap__ZN4Core8Platform11PosixThread11setPriorityEi(void *thread,
                                                     int priority) {
  __real__ZN4Core8Platform11PosixThread11setPriorityEi(thread, priority);
  if (capture)
    trace += "P " + std::to_string(static_cast<std::uint32_t>(priority)) + ";";
}

int main() {
  std::uint32_t counter;
  while (std::cin >> counter) {
    unsigned firstFlag, secondFlag, firstPort, secondPort, threadPresent;
    std::uint32_t initialPriority, interval, adapterInterval;
    std::cin >> firstFlag >> secondFlag >> firstPort >> secondPort >>
        initialPriority >> interval >> adapterInterval >> threadPresent;
    capture = false;
    trace.clear();
    trace.reserve(4096);
    lockDepth = 0;
    observedLock = nullptr;
    presonus::uc::CclFactoryRegistry registry;
    Presonus::UC::EventFactory factory(registry.registry());
    presonus::uc::EventDispatcherState dispatcherState;
    Presonus::UC::EventDispatcher dispatcher(dispatcherState);
    presonus::uc::NetworkManagerState state{dispatcher, factory};
    state.startedCount = signedWord(counter);
    state.primaryPortFlag = static_cast<std::uint8_t>(firstFlag);
    state.secondaryPortFlag = static_cast<std::uint8_t>(secondFlag);
    state.firstPort = static_cast<std::uint16_t>(firstPort);
    state.secondPort = static_cast<std::uint16_t>(secondPort);
    state.threadPriority = signedWord(initialPriority);
    state.processInterval = signedWord(interval);
    state.adapterInterval = adapterInterval;
    UnstartedThread thread;
    thread.setPriority(signedWord(initialPriority));
    state.processThread = threadPresent ? &thread : nullptr;
    FixtureConfigurationManager manager(state);
    unsigned externalCount;
    std::cin >> externalCount;
    for (unsigned index = 0; index < externalCount; ++index) {
      std::uint32_t value;
      std::cin >> value;
      check(dispatcherState.externalIDs.add(signedWord(value)));
    }
    unsigned operations;
    std::cin >> operations;
    expectedLock = &dispatcherState.handlerLock;
    std::ostringstream returns;
    capture = true;
    for (unsigned index = 0; index < operations; ++index) {
      unsigned op;
      std::uint32_t a, b, c;
      std::cin >> op >> a >> b >> c;
      int result;
      switch (op) {
      case 0:
        result = manager.setPortNumber(static_cast<unsigned short>(a),
                                       static_cast<unsigned short>(b),
                                       signedWord(c));
        break;
      case 1:
        result = manager.setNetworkPriority(signedWord(a));
        break;
      case 2:
        result = manager.isSendingFromExternalConnection(signedWord(a));
        break;
      default:
        std::abort();
      }
      check(lockDepth == 0);
      if (index)
        returns << ' ';
      returns << static_cast<std::uint32_t>(result);
    }
    capture = false;
    check(static_cast<bool>(std::cin));
    std::cout << returns.str() << '|' << trace << '|'
              << static_cast<unsigned>(state.primaryPortFlag) << ' '
              << static_cast<unsigned>(state.secondaryPortFlag) << ' '
              << state.firstPort << ' ' << state.secondPort << ' '
              << static_cast<std::uint32_t>(state.threadPriority) << ' '
              << static_cast<std::uint32_t>(state.processInterval) << ' '
              << state.adapterInterval << ' '
              << static_cast<std::uint32_t>(thread.getPriority()) << '\n';
  }
}
