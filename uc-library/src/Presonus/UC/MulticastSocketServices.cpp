#include "core/system/coredebug.h"
#include "core/system/coretime.h"
#include "presonus/uc/multicast_connection.hpp"
#include <cstdlib>
#include <cstring>
#include <sys/socket.h>
namespace presonus::uc {
static void appendSocket(SocketBundleState &bundle,
                         Core::Sockets::Socket *socket) {
  // Original unchecked capacity overflow is excluded from initialized domain.
  if (bundle.count < 0 || bundle.count >= 10)
    std::abort();
  bundle.sockets[bundle.count++] = socket;
}
static void sourceOption(Core::Sockets::Socket &socket, int originalOption,
                         int value) {
  using namespace Core::Sockets;
  // Original numeric calls remain verbatim in the evidence.104/105 meanings
  // are INFERRED and unresolved legacy Core semantics, not verified identities.
  switch (originalOption) {
  case 100:
    socket.setOption(SocketOption::kNonBlocking, value);
    break;
  case 101:
    socket.setOption(SocketOption::kBroadcast, value);
    break;
  case 104:
    socket.setOption(SocketOption::kReuseAddress, value);
    break;
  case 105:
    socket.setOption(SocketOption::kReusePort, value);
    break;
  default:
    std::abort();
  }
}
static void bindDevice(Core::Sockets::Socket &socket, const char *name) {
  // Actual CCL has no bindToDevice method. App-only descriptor adaptation.
  ::setsockopt(socket.getDescriptor(), SOL_SOCKET, SO_BINDTODEVICE, name,
               static_cast<socklen_t>(std::strlen(name) + 1));
}
static Core::Sockets::Socket *newDatagram() {
  using namespace Core::Sockets;
  return new Socket(kInternet, kDatagram, kUDP);
}
} // namespace presonus::uc
namespace Presonus::UC {
void SocketBundle::deleteAll() {
  for (int index = 0; index < state_.count; ++index)
    delete state_.sockets[index];
  state_.count = 0;
}
bool SocketBundle::isAnyError(int timeout) {
  for (int index = 0; index < state_.count; ++index)
    if (state_.sockets[index]->isAnyError(timeout))
      return true;
  return false;
}
void MulticastConnection::setMulticastGroupPending(bool pending) {
  state_.groupPending = pending;
  if (pending) {
    // Intentional actual CoreDebugPrintf diagnostic, not original report
    // routing.
    Core::DebugPrintf("UDP multicast group registration pending");
    state_.groupPending = 1;
    state_.pendingSinceMilliseconds =
        Core::SystemClock::getTime() /
        static_cast<std::int64_t>(Core::SystemClock::getFrequency() / 1000);
  } else
    state_.pendingSinceMilliseconds = 0;
}
void MulticastConnection::makeMulticastSockets(bool enabled) {
  state_.multicastEnabled = enabled;
  if (!enabled) {
    state_.multicast.deleteAll();
    setMulticastGroupPending(false);
    return;
  }
  auto configure = [&](const presonus::uc::AdapterIPAddress *adapter) {
    auto *socket = presonus::uc::newDatagram();
    presonus::uc::sourceOption(*socket, 104, 1);
    presonus::uc::sourceOption(*socket, 105, 1);
    presonus::uc::sourceOption(*socket, 100, 1);
    if (adapter) {
      Core::CStringBuffer<32> interfaceName;
      Core::Sockets::Network::getInterfaceNameForIP(interfaceName, *adapter);
      presonus::uc::bindDevice(*socket, interfaceName.str());
    }
    presonus::uc::AdapterIPAddress bindAddress;
    bindAddress.port = 47809;
    socket->bind(bindAddress);
    // Original app setOption(102,IPv4-group-bits) explicitly source-ports to
    // actual CCL membership API; original Core option semantics stay
    // unresolved.
    presonus::uc::AdapterIPAddress any;
    if (!socket->joinMulticastGroup(state_.group, any))
      setMulticastGroupPending(true);
    presonus::uc::appendSocket(state_.multicastStorage, socket);
  };
  if (!state_.adapterState.multiAddress)
    configure(nullptr);
  else {
    state_.adapter.getAddressList(false);
    for (int index = 0; index < state_.adapterState.storage.count; ++index) {
      const auto &address = state_.adapterState.storage.values[index];
      if (!address.isNull())
        configure(&address);
    }
  }
  Core::DebugPrintf("Enabled UDP multicast on official port %d (%d sockets)",
                    47809, state_.multicastStorage.count);
}
void MulticastConnection::makeUnicastSockets(bool enabled) {
  state_.unicastEnabled = enabled;
  if (!enabled) {
    state_.unicast.deleteAll();
    return;
  }
  if (!state_.adapterState.multiAddress) {
    auto *socket = presonus::uc::newDatagram();
    presonus::uc::sourceOption(*socket, 101, 1);
    presonus::uc::sourceOption(*socket, 100, 1);
    presonus::uc::AdapterIPAddress address;
    address.port = state_.configuredPort;
    if (address.port != 0)
      presonus::uc::sourceOption(*socket, 104, 1);
    socket->bind(address);
    presonus::uc::AdapterIPAddress local;
    socket->getLocalAddress(local);
    state_.boundPort = local.port;
    state_.configuredPort = local.port;
    presonus::uc::appendSocket(state_.unicastStorage, socket);
  } else {
    state_.boundPort = state_.configuredPort;
    state_.adapter.getAddressList(false);
    for (int index = 0; index < state_.adapterState.storage.count; ++index) {
      auto address = state_.adapterState.storage.values[index];
      if (address.isNull())
        continue;
      auto *socket = presonus::uc::newDatagram();
      presonus::uc::sourceOption(*socket, 101, 1);
      presonus::uc::sourceOption(*socket, 100, 1);
      presonus::uc::sourceOption(*socket, 104, 1);
      address.port = state_.configuredPort;
      socket->bind(address);
      presonus::uc::appendSocket(state_.unicastStorage, socket);
    }
  }
  Core::DebugPrintf("Local UDP port bound to %d (%d sockets)", state_.boundPort,
                    state_.unicastStorage.count);
}
void MulticastConnection::startUnicastListening() {
  if (!state_.unicastEnabled)
    makeUnicastSockets(true);
}
void MulticastConnection::addReceiver(IMulticastReceiver *receiver) {
  if (state_.receivers.count() == 0) {
    makeMulticastSockets(true);
    startUnicastListening();
  }
  state_.receivers.add(receiver);
}
void MulticastConnection::removeReceiver(IMulticastReceiver *receiver) {
  state_.receivers.remove(receiver);
  if (state_.receivers.count() == 0)
    makeMulticastSockets(false);
}
} // namespace Presonus::UC
