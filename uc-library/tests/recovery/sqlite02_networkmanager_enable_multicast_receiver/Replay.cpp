#include "../../network_next_services/fixture_next_manager.hpp"
#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/multicast_connection.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
class OtherReceiver final : public IMulticastReceiver {
  void onMulticastEvent(const char *, unsigned short, unsigned short, int,
                        EventItem *) override {
    std::abort();
  }
};
NetworkManagerState *active;
ConnectionHandler *trackedHandler;
MulticastConnection *trackedConnection;
IMulticastReceiver *trackedReceiver;
std::ostringstream trace;
} // namespace

extern "C" MulticastConnection *
__real__ZN8Presonus2UC17ConnectionHandler22getMulticastConnectionEv(
    ConnectionHandler *);
extern "C" void
__real__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *, IMulticastReceiver *);
extern "C" void
__real__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *, IMulticastReceiver *);

extern "C" MulticastConnection *
__wrap__ZN8Presonus2UC17ConnectionHandler22getMulticastConnectionEv(
    ConnectionHandler *handler) {
  if (handler != trackedHandler)
    std::abort();
  trace << " get:" << active->multicastReceiverEnabled;
  return __real__ZN8Presonus2UC17ConnectionHandler22getMulticastConnectionEv(
      handler);
}

extern "C" void
__wrap__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *connection, IMulticastReceiver *receiver) {
  if (connection != trackedConnection || receiver != trackedReceiver)
    std::abort();
  trace << " add:" << active->multicastReceiverEnabled;
  __real__ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE(
      connection, receiver);
}

extern "C" void
__wrap__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
    MulticastConnection *connection, IMulticastReceiver *receiver) {
  if (connection != trackedConnection || receiver != trackedReceiver)
    std::abort();
  trace << " remove:" << active->multicastReceiverEnabled;
  __real__ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE(
      connection, receiver);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool initial = std::atoi(argv[1]);
  const bool requested = std::atoi(argv[2]);
  EventDispatcher dispatcher;
  EventFactory factory;
  NetworkManagerState state{dispatcher, factory};
  FixtureNextManager manager(state);
  CclAdapterServices services;
  AdapterHandlerState adapterState(services);
  AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
  BasicConnectionState queue;
  MulticastConnectionState multicastState(queue, adapter, adapterState);
  MulticastConnection multicast(MulticastSourcePortTag{}, multicastState);
  ConnectionHandlerState handlerState;
  ConnectionHandler handler(handlerState);
  handlerState.multicastIdentity = &multicast;
  state.connectionHandler = &handler;
  state.multicastReceiverEnabled = initial;

  OtherReceiver other;
  multicastState.receivers.add(&other);
  auto *managerReceiver = static_cast<IMulticastReceiver *>(&manager);
  if (initial)
    multicastState.receivers.add(managerReceiver);
  active = &state;
  trackedHandler = &handler;
  trackedConnection = &multicast;
  trackedReceiver = managerReceiver;
  manager.enableMulticastReceiver(requested);
  if (multicastState.receivers.count() != 1 + requested ||
      multicastState.receivers.at(0) != &other ||
      (requested && multicastState.receivers.at(1) != managerReceiver) ||
      multicastState.unicastStorage.count ||
      multicastState.multicastStorage.count)
    return 3;
  std::cout << state.multicastReceiverEnabled << trace.str() << '\n';
}
