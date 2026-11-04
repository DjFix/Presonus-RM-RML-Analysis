#include "presonus/uc/server.hpp"
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string>

// Allocator instrumentation records only actual physical frees. Fixed storage
// avoids recursion; untracked framework/setup frees are deliberately excluded.
struct Tracked {
  void *pointer;
  std::string label;
  bool object;
};
static Tracked tracked[64];
static int trackedCount = 0;
struct Event {
  bool object;
  const char *label;
};
static Event events[64];
static int eventCount = 0;
static void track(void *p, const std::string &label, bool object = false) {
  if (p)
    tracked[trackedCount++] = {p, label, object};
}
static void record(void *p) {
  for (int i = 0; i < trackedCount; ++i)
    if (tracked[i].pointer == p) {
      events[eventCount++] = {tracked[i].object, tracked[i].label.c_str()};
      tracked[i].pointer = nullptr;
      return;
    }
}
void *operator new(std::size_t n) {
  if (auto *p = std::malloc(n))
    return p;
  throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept {
  record(p);
  std::free(p);
}
void operator delete[](void *p) noexcept {
  record(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept {
  ::operator delete[](p);
}

using namespace Presonus::UC;
extern "C" void serverD1(Server *) asm("_ZN8Presonus2UC6ServerD1Ev");
extern "C" void serverD0(Server *) asm("_ZN8Presonus2UC6ServerD0Ev");
extern "C" void
remoteD1(RemoteServer *) asm("_ZN8Presonus2UC12RemoteServerD1Ev");
extern "C" void
remoteD0(RemoteServer *) asm("_ZN8Presonus2UC12RemoteServerD0Ev");
extern "C" void
registrarD2(ServerRegistrar *) asm("_ZN8Presonus2UC15ServerRegistrarD2Ev");
class SourceServer : public Server {
public:
  SourceServer() : Server() {}
  int getType() const override { return 0; }
};
class Listener : public INetworkListener {
public:
  int calls = 0;
  void onServerAvailable(int, const ServerInfo &) override { ++calls; }
  void onServerUnavailable(int) override { ++calls; }
  void onServerChanged(int) override { ++calls; }
};
static void storage(Server &server, int n, const std::string &label) {
  for (int j = 0; j < n; ++j)
    server.sourcePortStorage().add(j + 1);
  track(server.sourcePortStorage().getItems(), label);
}
static void require(bool ok) {
  if (!ok)
    std::abort();
}
int main(int argc, char **argv) {
  require(argc == 5);
  int index = std::atoi(argv[1]), n = std::atoi(argv[2]),
      holes = std::atoi(argv[3]), s = std::atoi(argv[4]);
  if (index == 9) {
    presonus::uc::ServerState common;
    presonus::uc::RemoteServerState remoteState;
    LocalServer local(presonus::uc::ServerSourcePortTag{}, common);
    RemoteServer remote(presonus::uc::ServerSourcePortTag{}, remoteState);
    Listener listener;
    presonus::uc::AvailableServerView view;
    view.identity = &remote;
    presonus::uc::ServerRegistrarState state;
    state.remoteServers.add(&view);
    state.listeners.add(&listener);
    state.allServerViews.add(&view);
    {
      ServerRegistrar borrowed(state);
      require(!borrowed.sourcePortAddOwnedRemote(&remote, view));
    }
    require(state.remoteServers.count() == 1 && state.listeners.count() == 1 &&
            state.allServerViews.count() == 1 && local.getType() == 0 &&
            remote.getType() == 1 && listener.calls == 0);
    auto &singleton = ServerRegistrar::instance();
    require(&singleton == &ServerRegistrar::instance());
    std::printf("{\"borrowed_preserved\":true,\"singleton_stable\":true}\n");
    return 0;
  }
  if (index <= 2) {
    ServerRegistrar registrar;
    auto &state = registrar.sourcePortState();
    std::printf("{\"trace\":[],\"initial\":[%d,%d,%d,%d,%d,%d]}\n",
                state.localServers.count(), state.remoteServers.count(),
                state.listeners.count(), state.localServers.getDelta(),
                state.remoteServers.getDelta(), state.listeners.getDelta());
    require(state.allServerViews.count() == 0);
    return 0;
  }
  if (index <= 4) {
    ServerRegistrar *registrar = new ServerRegistrar;
    auto &state = registrar->sourcePortState();
    SourceServer local;
    Listener listener;
    presonus::uc::AvailableServerView views[5], locals[2];
    for (auto &v : locals) {
      v.identity = &local;
      state.localServers.add(&v);
      state.allServerViews.add(&v);
    }
    state.listeners.add(&listener);
    state.listeners.add(&listener);
    for (int k = 0; k < n; ++k) {
      if (holes && k % 2 == 1) {
        state.remoteServers.add(nullptr);
        continue;
      }
      auto *remote = new RemoteServer;
      require(registrar->sourcePortAddOwnedRemote(remote, views[k]));
      storage(*remote, s, "storage" + std::to_string(k));
      track(remote, "remote" + std::to_string(k), true);
    }
    track(state.localServers.getItems(), "local");
    track(state.remoteServers.getItems(), "remote");
    track(state.listeners.getItems(), "listener");
    if (index == 3)
      delete registrar;
    else {
      registrarD2(registrar);
      ::operator delete(registrar);
    }
    require(local.getType() == 0 && listener.calls == 0);
  } else {
    Server *server = index <= 6 ? static_cast<Server *>(new RemoteServer)
                                : static_cast<Server *>(new SourceServer);
    storage(*server, s, "storage");
    if (index % 2 == 0) {
      track(server, "object", true);
      if (index == 6)
        remoteD0(static_cast<RemoteServer *>(server));
      else
        serverD0(server);
    } else {
      if (index == 5)
        remoteD1(static_cast<RemoteServer *>(server));
      else
        serverD1(server);
      // D1 leaves object storage allocated. This explicit test-harness release
      // is untracked and never credited as a native D0 observation.
      ::operator delete(server);
    }
  }
  std::printf("{\"trace\":[");
  for (int i = 0; i < eventCount; ++i)
    std::printf("%s[\"%s\",\"%s\"]", i ? "," : "",
                events[i].object ? "delete" : "free", events[i].label);
  std::printf("]}\n");
  for (int i = 0; i < trackedCount; ++i)
    require(tracked[i].pointer == nullptr);
  return 0;
}
