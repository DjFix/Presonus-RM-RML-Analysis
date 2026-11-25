#include "presonus/uc/multicast_connection.hpp"
#include <array>
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <iostream>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
std::array<int, 2> tracked;
std::array<char, 2> closureOrder;
std::size_t closed = 0;
const MulticastConnectionState *active = nullptr;
bool markerSetDuringClosure = true;
} // namespace

extern "C" int __real_close(int);
extern "C" int __wrap_close(int descriptor) {
  if (active && (descriptor == tracked[0] || descriptor == tracked[1])) {
    if (closed >= closureOrder.size())
      std::abort();
    closureOrder[closed++] = descriptor == tracked[0] ? 'U' : 'M';
    markerSetDuringClosure &= active->resetMarker == 1;
  }
  return __real_close(descriptor);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  CclAdapterServices provider;
  AdapterHandlerState adapterState(provider);
  adapterState.cacheValid = 1;
  adapterState.multiAddress = 1;
  AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
  BasicConnectionState queue;
  MulticastConnectionState state(queue, adapter, adapterState);
  MulticastConnection connection(MulticastSourcePortTag{}, state);
  state.unicastEnabled = std::atoi(argv[1]);
  state.multicastEnabled = std::atoi(argv[2]);
  state.resetMarker = 0x36;
  using namespace Core::Sockets;
  auto seed = [](SocketBundleState &bundle) {
    auto *socket = new Socket(kInternet, kDatagram, kUDP);
    const int descriptor = socket->getDescriptor();
    if (descriptor < 0)
      std::abort();
    bundle.sockets[0] = socket;
    bundle.count = 1;
    return descriptor;
  };
  tracked = {seed(state.unicastStorage), seed(state.multicastStorage)};
  active = &state;
  connection.reset();
  active = nullptr;
  for (std::size_t index = 0; index < tracked.size(); ++index) {
    const bool wasClosed =
        fcntl(tracked[index], F_GETFD) == -1 && errno == EBADF;
    const bool wasEnabled = std::atoi(argv[index + 1]) != 0;
    const auto &bundle =
        index == 0 ? state.unicastStorage : state.multicastStorage;
    if (wasClosed != wasEnabled || bundle.count != (wasEnabled ? 0 : 1))
      return 3;
  }
  std::cout << unsigned(state.resetMarker) << ' '
            << unsigned(state.unicastEnabled) << ' '
            << unsigned(state.multicastEnabled) << ' ' << markerSetDuringClosure
            << ' ';
  std::cout.write(closureOrder.data(), closed);
  std::cout << '\n';
  connection.cleanup();
}
