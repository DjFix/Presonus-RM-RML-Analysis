#include "../../network_next_services/fixture_next_manager.hpp"
#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string_view>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
NetworkManagerState *active;
EventQueueState *trackedQueue;
NetworkManager *trackedManager;
std::ostringstream trace;
bool drain;
} // namespace

extern "C" void __real__ZN4Core8Platform13CurrentThread5sleepEj(unsigned);
extern "C" bool
__real__ZN8Presonus2UC14NetworkManager17hasOutgoingEventsEv(NetworkManager *);

extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned ms) {
  if (active)
    trace << " sleep:" << unsigned(active->waitingForOutgoingEvents) << ':'
          << ms;
  __real__ZN4Core8Platform13CurrentThread5sleepEj(ms);
  if (active && drain)
    trackedQueue->head = nullptr;
}

extern "C" bool __wrap__ZN8Presonus2UC14NetworkManager17hasOutgoingEventsEv(
    NetworkManager *manager) {
  if (manager != trackedManager)
    std::abort();
  const bool result =
      __real__ZN8Presonus2UC14NetworkManager17hasOutgoingEventsEv(manager);
  trace << " poll:" << unsigned(active->waitingForOutgoingEvents) << ':'
        << result;
  return result;
}

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  const std::string_view scenario(argv[3]);
  EventDispatcher dispatcher;
  EventFactory factory;
  NetworkManagerState state{dispatcher, factory};
  FixtureNextManager manager(state);
  ConnectionHandlerState handlerState;
  ConnectionHandler handler(handlerState);
  EventQueueState storage;
  EventQueue queue(storage);
  BasicConnectionState outgoing;
  outgoing.queue = &queue;
  outgoing.storage = &storage;
  BasicConnection multicast(outgoing);
  handlerState.multicastOutgoing = &multicast;
  state.connectionHandler = &handler;

  OwnedCodecItem<BinaryEvent> item;
  EventQueueNode node{&item};
  if (scenario != "empty")
    storage.head = &node;
  drain = scenario == "drain";
  state.waitingForOutgoingEvents = std::atoi(argv[1]);
  trackedManager = &manager;
  trackedQueue = &storage;
  active = &state;
  const int result =
      manager.NetworkManager::waitForOutgoingEvents(std::atoi(argv[2]));
  active = nullptr;
  storage.head = nullptr;
  std::cout << result << ' ' << unsigned(state.waitingForOutgoingEvents)
            << trace.str() << '\n';
}
