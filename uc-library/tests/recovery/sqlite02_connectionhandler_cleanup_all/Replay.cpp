#include "presonus/uc/connection_handler.hpp"
#include "presonus/uc/external_connection.hpp"
#include "presonus/uc/multicast_connection.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <iostream>
#include <sstream>
#include <string_view>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
std::ostringstream trace;
bool observed = false;
std::array<void *, 4> allocated{};
std::array<bool, 4> released{};

int identity(void *pointer) {
  if (!pointer)
    return 0;
  auto entry = std::find(allocated.begin() + 1, allocated.end(), pointer);
  if (entry == allocated.end())
    std::abort();
  return static_cast<int>(entry - allocated.begin());
}

struct ConnectionFixture {
  ExternalConnectionState external;
  ConnectionState common;
  BasicConnectionState outgoing;
  HandlerConnectionView view;
};

class TrackedConnection final : public ExternalConnection {
public:
  TrackedConnection(ConnectionFixture &fixture, int identifier)
      : ExternalConnection(fixture.external, fixture.common, fixture.outgoing),
        identifier_(identifier) {}
  ~TrackedConnection() override {
    if (observed) {
      trace << " destroy:" << identifier_;
      observeDestruction();
    }
  }
  static void *operator new(std::size_t size) { return ::operator new(size); }
  static void operator delete(void *pointer) {
    const int identifier = identity(pointer);
    if (released[identifier])
      std::abort();
    released[identifier] = true;
    if (observed)
      trace << " deallocate:" << identifier;
    ::operator delete(pointer);
  }
  bool process(bool) override { std::abort(); }

private:
  int identifier_;
  static void observeDestruction();
};

void printRoster(std::ostream &out, const Core::Vector<Connection *> &roster) {
  out << '[';
  for (int index = 0; index < roster.count(); ++index) {
    if (index)
      out << ',';
    out << identity(roster.at(index));
  }
  out << ']';
}

void seed(ConnectionHandlerState &state, Core::Vector<Connection *> &roster,
          std::array<ConnectionFixture, 4> &objects, std::string_view ids) {
  for (auto id : ids) {
    const int identifier = id - '0';
    if (identifier < 0 || identifier >= static_cast<int>(objects.size()))
      std::abort();
    if (!identifier) {
      roster.add(nullptr);
      continue;
    }
    auto &fixture = objects[identifier];
    if (allocated[identifier])
      std::abort();
    auto *connection = new TrackedConnection(fixture, identifier);
    allocated[identifier] = connection;
    fixture.view.identity = connection;
    fixture.view.common = &fixture.common;
    fixture.view.outgoing = connection;
    roster.add(connection);
    state.views.add(&fixture.view);
  }
}

void cleanupFixtures() {
  for (std::size_t id = 1; id < allocated.size(); ++id) {
    if (allocated[id] && !released[id])
      delete static_cast<TrackedConnection *>(allocated[id]);
  }
}

void checkViews(const ConnectionHandlerState &state) {
  for (auto *view : state.views)
    if (released[identity(view->identity)])
      std::abort();
}

std::array<int, 3> trackedSockets{-1, -1, -1};
constexpr std::array<const char *, 3> socketNames{"listen", "unicast",
                                                  "multicast"};

void seedSocket(SocketBundleState &slots, std::size_t index) {
  using namespace Core::Sockets;
  auto *socket = new Socket(kInternet, kDatagram, kUDP);
  trackedSockets[index] = socket->getDescriptor();
  if (trackedSockets[index] < 0)
    std::abort();
  slots.sockets[0] = socket;
  slots.count = 1;
}

void verifySocket(const SocketBundleState &slots, std::size_t index) {
  const int descriptor = trackedSockets[index];
  if (descriptor < 0)
    return;
  const bool closed = fcntl(descriptor, F_GETFD) < 0 && errno == EBADF;
  if (closed != (slots.count == 0))
    std::abort();
}

void TrackedConnection::observeDestruction() {}
} // namespace

extern "C" int __real_close(int);
extern "C" int __wrap_close(int descriptor) {
  const auto entry =
      std::find(trackedSockets.begin(), trackedSockets.end(), descriptor);
  if (observed && entry != trackedSockets.end())
    trace << " close:" << socketNames[entry - trackedSockets.begin()];
  return __real_close(descriptor);
}

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  std::array<ConnectionFixture, 4> objects;
  ConnectionHandlerState state;
  ConnectionHandler handler(state);
  CclAdapterServices services;
  AdapterHandlerState adapterState(services);
  AdapterHandler adapter(AdapterSourcePortTag{}, adapterState);
  BasicConnectionState queue;
  MulticastConnectionState multicastState(queue, adapter, adapterState);
  MulticastConnection multicast(MulticastSourcePortTag{}, multicastState);
  state.multicastIdentity = &multicast;
  state.listeningEnabled = std::atoi(argv[4]);
  multicastState.unicastEnabled = multicastState.multicastEnabled = 1;
  seedSocket(multicastState.unicastStorage, 1);
  seedSocket(multicastState.multicastStorage, 2);
  seed(state, state.listeningConnections, objects, argv[1]);
  seed(state, state.localConnections, objects, argv[2]);
  seed(state, state.externalConnections, objects, argv[3]);

  observed = true;
  handler.cleanupAll();
  observed = false;
  if (state.listeningConnections.getCapacity() ||
      state.localConnections.getCapacity() ||
      state.externalConnections.getCapacity() ||
      multicastState.unicastStorage.count ||
      multicastState.multicastStorage.count || multicastState.unicastEnabled ||
      multicastState.multicastEnabled)
    return 3;
  verifySocket(multicastState.unicastStorage, 1);
  verifySocket(multicastState.multicastStorage, 2);
  checkViews(state);
  printRoster(std::cout, state.listeningConnections);
  printRoster(std::cout, state.localConnections);
  printRoster(std::cout, state.externalConnections);
  std::cout << ' ' << unsigned(state.listeningEnabled) << trace.str() << '\n';
  cleanupFixtures();
}
