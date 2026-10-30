#include "fixture_next_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <type_traits>

using Reporter = Presonus::UC::INetworkErrorReporter;
using ReporterPtr = Reporter *;
int invokeReporter(Presonus::UC::INetworkManager &, bool, ReporterPtr);
namespace {
enum class Capture { Off, Seed, Run };
struct NodeRecord {
  void *address = nullptr;
  unsigned id = 0;
  bool live = false;
};
struct Event {
  char kind;
  unsigned value;
};
Capture capture = Capture::Off;
std::array<NodeRecord, 64> nodes;
std::array<Event, 256> events;
unsigned nodeCount = 0, eventCount = 0;
Core::Threads::Lock *activeLock = nullptr;
Core::LinkedList<ReporterPtr> *activeList = nullptr;
void *activePlatformLock = nullptr;
constexpr auto nodeSize = sizeof(Core::ListLink<ReporterPtr>);
static_assert(std::is_standard_layout_v<Core::ListLink<ReporterPtr>>);
static_assert(nodeSize == 3 * sizeof(void *));
void check(bool condition) {
  if (!condition)
    std::abort();
}
void event(char kind, unsigned value = 0) {
  check(eventCount < events.size());
  events[eventCount++] = {kind, value};
}
NodeRecord &record(void *address) {
  for (unsigned n = 0; n < nodeCount; ++n)
    if (nodes[n].address == address && nodes[n].live)
      return nodes[n];
  std::abort();
}
void observeLock(void *platform) {
  const auto begin = reinterpret_cast<std::uintptr_t>(activeLock);
  const auto address = reinterpret_cast<std::uintptr_t>(platform);
  check(activeLock && address >= begin &&
        address < begin + sizeof(*activeLock));
  if (!activePlatformLock)
    activePlatformLock = platform;
  check(activePlatformLock == platform);
}
void beforeDelete(void *address) {
  auto &node = record(address);
  check(node.live);
  // Inspect the surviving live list, never bytes of an ended ListLink lifetime.
  check(activeList != nullptr);
  unsigned reachable = 0;
  for (Core::ListIterator<ReporterPtr> it(*activeList); !it.done();) {
    ReporterPtr &value = it.next();
    check(static_cast<void *>(&value) != address);
    ++reachable;
  }
  unsigned trackedLive = 0;
  for (unsigned n = 0; n < nodeCount; ++n)
    trackedLive += nodes[n].live;
  check(reachable + 1 == trackedLive);
}
} // namespace
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void *__wrap__Znwm(std::size_t size) {
  void *result = __real__Znwm(size);
  if (capture != Capture::Off) {
    check(size == nodeSize && nodeCount < nodes.size());
    ++nodeCount;
    nodes[nodeCount - 1] = {result, nodeCount, true};
    if (capture == Capture::Run)
      event('A', nodeCount);
  }
  return result;
}
extern "C" void __wrap__ZdlPv(void *address) noexcept {
  unsigned id = 0;
  if (capture == Capture::Run) {
    beforeDelete(address);
    id = record(address).id;
  }
  __real__ZdlPv(address);
  if (capture == Capture::Run) {
    nodes[id - 1].live = false;
    event('D', id);
  }
}
extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) noexcept {
  unsigned id = 0;
  if (capture == Capture::Run) {
    check(size == nodeSize);
    beforeDelete(address);
    id = record(address).id;
  }
  __real__ZdlPvm(address, size);
  if (capture == Capture::Run) {
    nodes[id - 1].live = false;
    event('D', id);
  }
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *platform) {
  if (capture == Capture::Run) {
    observeLock(platform);
    event('L');
  }
  __real__ZN4Core8Platform9PosixLock4lockEv(platform);
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *platform) {
  if (capture == Capture::Run)
    observeLock(platform);
  __real__ZN4Core8Platform9PosixLock6unlockEv(platform);
  if (capture == Capture::Run)
    event('U');
}
int main() {
  try {
    std::uint32_t started;
    unsigned seedCount;
    while (std::cin >> started >> seedCount) {
      check(seedCount <= 8);
      std::array<unsigned, 8> seed;
      for (unsigned n = 0; n < seedCount; ++n)
        std::cin >> seed[n];
      unsigned operationCount;
      std::cin >> operationCount;
      check(operationCount <= 12);
      std::array<std::pair<unsigned, unsigned>, 12> operations;
      for (unsigned n = 0; n < operationCount; ++n)
        std::cin >> operations[n].first >> operations[n].second;
      check(static_cast<bool>(std::cin));
      capture = Capture::Off;
      nodeCount = eventCount = 0;
      activePlatformLock = nullptr;
      presonus::uc::CclFactoryRegistry registry;
      Presonus::UC::EventFactory factory(registry.registry());
      presonus::uc::EventDispatcherState dispatcherState;
      Presonus::UC::EventDispatcher dispatcher(dispatcherState);
      presonus::uc::NetworkManagerState state{dispatcher, factory};
      std::memcpy(&state.startedCount, &started, sizeof started);
      FixtureNextManager manager(state);
      Presonus::UC::INetworkManager &interface = manager;
      std::array<std::uint64_t, 7> tokenStorage{};
      auto token = [&](unsigned id) -> ReporterPtr {
        check(id <= 6);
        return id ? reinterpret_cast<ReporterPtr>(&tokenStorage[id]) : nullptr;
      };
      auto tokenID = [&](ReporterPtr value) {
        for (unsigned n = 1; n <= 6; ++n)
          if (token(n) == value)
            return n;
        std::abort();
      };
      activeLock = &state.errorReporterLock;
      activeList = &state.errorReporters;
      capture = Capture::Seed;
      for (unsigned n = 0; n < seedCount; ++n) {
        check(seed[n] >= 1 && seed[n] <= 6);
        state.errorReporters.append(token(seed[n]));
      }
      capture = Capture::Run;
      const bool sameLock =
          manager.getLock() == activeLock && manager.getLock() == activeLock;
      const bool isStarted = manager.isStarted();
      std::array<int, 12> results;
      for (unsigned n = 0; n < operationCount; ++n) {
        auto [op, id] = operations[n];
        check(op <= 1);
        results[n] = invokeReporter(interface, op != 0, token(id));
      }
      capture = Capture::Off;
      std::cout << static_cast<unsigned>(isStarted) << ' '
                << static_cast<unsigned>(sameLock) << '|';
      for (unsigned n = 0; n < operationCount; ++n) {
        if (n)
          std::cout << ' ';
        std::cout << results[n];
      }
      std::cout << '|';
      for (unsigned n = 0; n < eventCount; ++n) {
        std::cout << events[n].kind;
        if (events[n].kind == 'A' || events[n].kind == 'D')
          std::cout << ' ' << events[n].value;
        std::cout << ';';
      }
      std::cout << '|' << state.errorReporters.count();
      unsigned live = 0;
      for (Core::ListIterator<ReporterPtr> iterator(state.errorReporters);
           !iterator.done();) {
        ReporterPtr &value = iterator.next();
        auto &node = record(static_cast<void *>(&value));
        ++live;
        std::cout << ' ' << node.id << ' ' << tokenID(value);
      }
      unsigned trackedLive = 0;
      for (unsigned n = 0; n < nodeCount; ++n)
        trackedLive += nodes[n].live;
      check(live == trackedLive);
      std::cout << '\n';
      activeLock = nullptr;
      activeList = nullptr;
    }
    check(std::cin.eof());
  } catch (...) {
    capture = Capture::Off;
    return 1;
  }
}
