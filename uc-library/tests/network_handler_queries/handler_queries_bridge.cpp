#include "connection_fixture.hpp"
#include "fixture_handler_query_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/connection_handler.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <optional>
#include <string>

namespace {
bool capture = false;
std::string trace;
int lockDepth = 0;
Core::Threads::Lock *expectedLock = nullptr;
void *observedLock = nullptr;
std::array<const Presonus::UC::BasicConnection *, 7> outgoingIdentities;
void check(bool condition) {
  if (!condition)
    std::abort();
}
std::int32_t signedWord(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
void observe(void *lock) {
  auto p = reinterpret_cast<std::uintptr_t>(lock);
  auto start = reinterpret_cast<std::uintptr_t>(expectedLock);
  check(expectedLock && p >= start && p < start + sizeof(*expectedLock));
  if (!observedLock)
    observedLock = lock;
  check(observedLock == lock);
}
} // namespace
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" bool __real__ZNK8Presonus2UC15BasicConnection15hasQueuedEventsEv(
    const Presonus::UC::BasicConnection *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *lock) {
  if (capture) {
    observe(lock);
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
    observe(lock);
    check(lockDepth == 1);
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
  if (capture) {
    lockDepth = 0;
    trace += "U;";
  }
}
extern "C" bool __wrap__ZNK8Presonus2UC15BasicConnection15hasQueuedEventsEv(
    const Presonus::UC::BasicConnection *connection) {
  if (capture) {
    unsigned id = 0;
    for (unsigned n = 0; n < outgoingIdentities.size(); ++n)
      if (outgoingIdentities[n] == connection)
        id = n + 1;
    check(id != 0);
    trace += "Q " + std::to_string(id) + ";";
  }
  return __real__ZNK8Presonus2UC15BasicConnection15hasQueuedEventsEv(
      connection);
}

int main() {
  unsigned enabled;
  while (std::cin >> enabled) {
    capture = false;
    trace.clear();
    trace.reserve(4096);
    lockDepth = 0;
    observedLock = nullptr;
    std::array<presonus::uc::ConnectionState, 6> connectionStates;
    std::array<std::optional<hierarchy_test::ConcreteConnection>, 6>
        connections;
    std::array<presonus::uc::BasicConnectionState, 7> basicStates;
    std::array<std::optional<Presonus::UC::BasicConnection>, 7> basics;
    std::array<presonus::uc::EventQueueState, 7> queues;
    std::array<presonus::uc::EventQueueNode, 7> nodes;
    std::array<std::array<presonus::uc::ConnectionSenderView, 8>, 6> senders;
    std::array<std::array<std::uint64_t, 8>, 6> senderTokens;
    std::array<presonus::uc::HandlerConnectionView, 6> views;
    std::array<std::uint64_t, 8> channelTokens{};
    auto channel = [&](unsigned id) -> Presonus::UC::IDataChannel * {
      check(id < channelTokens.size());
      return id ? reinterpret_cast<Presonus::UC::IDataChannel *>(
                      &channelTokens[id])
                : nullptr;
    };
    presonus::uc::ConnectionHandlerState handlerState;
    handlerState.listeningEnabled = static_cast<unsigned char>(enabled);
    for (unsigned n = 0; n < 6; ++n) {
      unsigned channelID, disabled, queued, count;
      std::cin >> channelID >> disabled >> queued >> count;
      check(count <= 8);
      for (unsigned index = 0; index < count; ++index) {
        std::uint32_t value;
        std::cin >> value;
        senders[n][index] = {&senderTokens[n][index], value ^ 0xffffffffU,
                             value};
      }
      connectionStates[n].senders = senders[n].data();
      connectionStates[n].senderCount = count;
      connections[n].emplace(connectionStates[n]);
      queues[n].head = queued ? &nodes[n] : nullptr;
      basicStates[n].storage = &queues[n];
      basics[n].emplace(basicStates[n]);
      outgoingIdentities[n] = &*basics[n];
      views[n] = {&*connections[n], &*basics[n], &connectionStates[n],
                  channel(channelID), static_cast<unsigned char>(disabled)};
      check(handlerState.views.add(&views[n]));
    }
    Core::Vector<Presonus::UC::Connection *> custom;
    for (auto *items : {&handlerState.localConnections,
                        &handlerState.externalConnections, &custom}) {
      unsigned count;
      std::cin >> count;
      for (unsigned index = 0; index < count; ++index) {
        unsigned identifier;
        std::cin >> identifier;
        check(identifier >= 1 && identifier <= 6);
        check(items->add(&*connections[identifier - 1]));
      }
    }
    unsigned multicastQueued, queryChannel;
    std::uint32_t queryKey;
    std::cin >> multicastQueued >> queryChannel >> queryKey;
    queues[6].head = multicastQueued ? &nodes[6] : nullptr;
    basicStates[6].storage = &queues[6];
    basics[6].emplace(basicStates[6]);
    outgoingIdentities[6] = &*basics[6];
    std::uint64_t multicastToken = 0;
    handlerState.multicastIdentity =
        reinterpret_cast<Presonus::UC::MulticastConnection *>(&multicastToken);
    handlerState.multicastOutgoing = &*basics[6];
    Presonus::UC::ConnectionHandler handler(handlerState);
    presonus::uc::CclFactoryRegistry registry;
    Presonus::UC::EventFactory factory(registry.registry());
    presonus::uc::EventDispatcherState dispatcherState;
    Presonus::UC::EventDispatcher dispatcher(dispatcherState);
    presonus::uc::NetworkManagerState managerState{dispatcher, factory};
    managerState.connectionHandler = &handler;
    FixtureHandlerQueryManager manager(managerState);
    expectedLock = &managerState.errorReporterLock;
    capture = true;
    const auto identity = handler.getMulticastConnection();
    check(identity == handlerState.multicastIdentity);
    const auto enabledResult = handler.isListeningEnabled();
    auto *found = handler.findExternal(channel(queryChannel));
    unsigned foundID = 0;
    for (unsigned n = 0; n < 6; ++n)
      if (found == &*connections[n])
        foundID = n + 1;
    check(foundID != 0 || found == nullptr);
    const bool sending =
        handler.isSendingFromExternalConnection(signedWord(queryKey));
    const bool events = handler.hasEvents(custom);
    const bool outgoing = handler.hasOutgoingEvents();
    const bool managerOutgoing = manager.hasOutgoingEvents();
    capture = false;
    check(lockDepth == 0 && std::cin);
    std::cout << "1 " << static_cast<unsigned>(enabledResult) << ' ' << foundID
              << ' ' << sending << ' ' << events << ' ' << outgoing << ' '
              << managerOutgoing << '|' << trace << '\n';
  }
}
