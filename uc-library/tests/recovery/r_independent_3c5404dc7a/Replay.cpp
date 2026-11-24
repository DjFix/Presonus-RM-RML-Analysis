#include "presonus/uc/multicast_connection.hpp"

#include <cerrno>
#include <fcntl.h>
#include <iostream>
#include <unistd.h>

namespace {
bool closed(int fd) { return fcntl(fd, F_GETFD) == -1 && errno == EBADF; }
} // namespace

int main() {
  for (bool preexisting : {false, true}) {
    presonus::uc::BasicConnectionState basic;
    presonus::uc::CclAdapterServices services;
    presonus::uc::AdapterHandlerState adapters(services);
    Presonus::UC::AdapterHandler adapter(presonus::uc::AdapterSourcePortTag{},
                                         adapters);
    presonus::uc::MulticastConnectionState state(basic, adapter, adapters);
    Presonus::UC::MulticastConnection connection(
        presonus::uc::MulticastSourcePortTag{}, state);

    int descriptors[2] = {-1, -1};
    if (preexisting) {
      if (pipe(descriptors) != 0)
        return 1;
      state.unicastStorage.sockets[0] =
          new Core::Sockets::Socket(descriptors[0]);
      state.multicastStorage.sockets[0] =
          new Core::Sockets::Socket(descriptors[1]);
      state.unicastStorage.count = state.multicastStorage.count = 1;
      state.unicastEnabled = state.multicastEnabled = state.groupPending = 1;
      state.pendingSinceMilliseconds = 123;
    }
    for (int attempt = 0; attempt < 2; ++attempt) {
      connection.cleanup();
      const bool socketsClosed =
          !preexisting || (closed(descriptors[0]) && closed(descriptors[1]));
      std::cout << preexisting << ' ' << attempt << ' '
                << static_cast<int>(state.unicastEnabled) << ' '
                << static_cast<int>(state.multicastEnabled) << ' '
                << static_cast<int>(state.groupPending) << ' '
                << state.pendingSinceMilliseconds << ' '
                << state.unicastStorage.count << ' '
                << state.multicastStorage.count << ' ' << socketsClosed << '\n';
    }
  }
}
