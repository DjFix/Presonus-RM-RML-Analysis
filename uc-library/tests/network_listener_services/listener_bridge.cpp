#include "fixture_listener_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/server_registrar.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

using namespace Presonus::UC;
namespace {
std::string trace;
bool capture = false;
int lockDepth = 0;
Core::Threads::Lock *expectedLock = nullptr;
void *observedPlatformLock = nullptr;
void check(bool ok) {
  if (!ok)
    std::abort();
}
void observe(void *lock) {
  auto address = reinterpret_cast<std::uintptr_t>(lock);
  auto expected = reinterpret_cast<std::uintptr_t>(expectedLock);
  check(expectedLock && address >= expected &&
        address < expected + sizeof(*expectedLock));
  if (!observedPlatformLock)
    observedPlatformLock = lock;
  check(observedPlatformLock == lock);
}
struct Discovery final : presonus::uc::NetworkDiscoveryControl {
  void startListening() override { trace += "S;"; }
  void stopListening() override { trace += "T;"; }
};
struct Listener final : INetworkListener {
  void onServerUnavailable(int) override { std::abort(); }
  void onServerChanged(int) override { std::abort(); }
  unsigned identifier = 0;
  void onServerAvailable(int id, const ServerInfo &info) override {
    check(info.originalDescriptorSize == 24);
    trace += "B " + std::to_string(identifier) + " " +
             std::to_string(static_cast<std::uint32_t>(id)) + " " +
             std::to_string(info.flags) + " ";
    for (unsigned index = 0; index < 4; ++index) {
      check(info.strings[index] && info.strings[index][0] == 's');
      if (index)
        trace += ',';
      trace += info.strings[index] + 1;
    }
    trace += ';';
  }
};
} // namespace
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *lock) {
  if (capture) {
    observe(lock);
    check(lockDepth == 0);
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (capture) {
    ++lockDepth;
    trace += "L;";
  }
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *lock) {
  if (capture) {
    observe(lock);
    check(lockDepth == 1);
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
  if (capture) {
    --lockDepth;
    trace += "U;";
  }
}

int main() {
  std::uint32_t counter;
  while (std::cin >> counter) {
    trace.clear();
    trace.reserve(65536);
    lockDepth = 0;
    observedPlatformLock = nullptr;
    presonus::uc::CclFactoryRegistry registry;
    EventFactory factory(registry.registry());
    presonus::uc::EventDispatcherState dispatcherState;
    EventDispatcher dispatcher(dispatcherState);
    presonus::uc::ServerRegistrarState registrarState;
    ServerRegistrar registrar(registrarState);
    presonus::uc::NetworkManagerState managerState{dispatcher, factory};
    managerState.startedCount = static_cast<std::int32_t>(counter);
    managerState.registrar = &registrar;
    Discovery discovery;
    managerState.discovery = &discovery;
    FixtureListenerManager manager(managerState);
    std::array<Listener, 6> listeners;
    for (unsigned index = 0; index < listeners.size(); ++index)
      listeners[index].identifier = index + 1;
    auto listener = [&](unsigned id) -> INetworkListener * {
      check(id <= listeners.size());
      return id ? &listeners[id - 1] : nullptr;
    };
    unsigned seedCount, capacity;
    std::cin >> seedCount;
    for (unsigned index = 0, id; index < seedCount; ++index) {
      std::cin >> id;
      check(registrarState.listeners.add(listener(id)));
    }
    std::cin >> capacity;
    check(capacity >= seedCount);
    check(registrarState.listeners.resize(static_cast<int>(capacity)));
    std::array<presonus::uc::AvailableServerView, 12> servers;
    std::array<std::array<std::string, 4>, 12> strings;
    unsigned serverCount = 0;
    for (unsigned group = 0; group < 2; ++group) {
      unsigned count;
      std::cin >> count;
      for (unsigned index = 0; index < count; ++index) {
        check(serverCount < servers.size());
        auto &server = servers[serverCount];
        std::uint32_t id;
        unsigned hidden;
        std::cin >> id >> server.flags >> hidden;
        server.identifier = static_cast<int>(id);
        server.hidden = hidden != 0;
        for (unsigned field = 0; field < 4; ++field) {
          strings[serverCount][field] =
              "s" + std::to_string(serverCount * 4 + field);
          server.strings[field] = strings[serverCount][field].c_str();
        }
        check(
            (group ? registrarState.remoteServers : registrarState.localServers)
                .add(&server));
        ++serverCount;
      }
    }
    std::ostringstream returns;
    bool first = true;
    auto result = [&](unsigned value) {
      if (!first)
        returns << ' ';
      first = false;
      returns << value;
    };
    unsigned operations;
    std::cin >> operations;
    expectedLock = &managerState.errorReporterLock;
    capture = true;
    for (unsigned index = 0; index < operations; ++index) {
      unsigned op, id;
      std::cin >> op >> id;
      switch (op) {
      case 0:
        result(manager.registerListener(listener(id)));
        break;
      case 1:
        result(manager.unregisterListener(listener(id)));
        break;
      case 2:
        registrar.addListener(listener(id));
        break;
      case 3:
        registrar.removeListener(listener(id));
        break;
      case 4:
        registrar.notifyAvailable(listener(id));
        break;
      case 5:
        result(registrar.hasListeners());
        break;
      default:
        std::abort();
      }
      check(lockDepth == 0);
    }
    capture = false;
    std::cout << returns.str() << '|' << trace << '|'
              << registrarState.listeners.count();
    for (int index = 0; index < registrarState.listeners.count(); ++index) {
      auto *pointer = registrarState.listeners.at(index);
      unsigned id = 0;
      for (unsigned candidate = 0; candidate < listeners.size(); ++candidate)
        if (pointer == &listeners[candidate])
          id = candidate + 1;
      check(pointer == listener(id));
      std::cout << ' ' << id;
    }
    std::cout << '\n';
    check(static_cast<bool>(std::cin));
  }
}
