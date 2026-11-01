#include "presonus/MeterManagerBase.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using Presonus::MeterManagerBase;
struct Env final : presonus::meter::Environment, Presonus::UC::INetworkManager {
  // Boundary test double: unrelated services abort if unexpectedly reached.
  int handleEvent(void *, const Presonus::UC::Event &) override {
    std::abort();
  }
  int startup(unsigned char) override { std::abort(); }
  int shutdown() override { std::abort(); }
  int setPortNumber(unsigned short, unsigned short, int) override {
    std::abort();
  }
  int setLocalName(const char *) override { std::abort(); }
  int setNetworkPriority(int) override { std::abort(); }
  int registerListener(Presonus::UC::INetworkListener *) override {
    std::abort();
  }
  int unregisterListener(Presonus::UC::INetworkListener *) override {
    std::abort();
  }
  int registerServer(int &, Presonus::UC::IEventHandler *,
                     const Presonus::UC::ServerInfo &, int) override {
    std::abort();
  }
  int unregisterServer(Presonus::UC::IEventHandler *) override { std::abort(); }
  int updateServer(Presonus::UC::IEventHandler *) override { std::abort(); }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const Presonus::UC::ServerInfo &) override {
    std::abort();
  }
  int removeRemoteServer(int) override { std::abort(); }
  int registerHandler(int &, Presonus::UC::IEventHandler *) override {
    std::abort();
  }
  int unregisterHandler(Presonus::UC::IEventHandler *) override {
    std::abort();
  }
  int sendMulticastEvent(const Presonus::UC::Event &) override { std::abort(); }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    std::abort();
  }
  int processIdle() override { std::abort(); }
  int getServerContextInfo(Presonus::UC::ServerContextInfo &, int) override {
    std::abort();
  }
  int addExternalConnection(Presonus::UC::IConnection *&,
                            Presonus::UC::IDataChannel *, int, unsigned char,
                            Presonus::UC::IEventHandler *) override {
    std::abort();
  }
  int updateExternalConnection(Presonus::UC::IDataChannel *, int) override {
    std::abort();
  }
  int removeExternalConnection(Presonus::UC::IDataChannel *) override {
    std::abort();
  }
  int rescanAll(unsigned char) override { std::abort(); }
  int resetConnection() override { std::abort(); }
  int addErrorReporter(Presonus::UC::INetworkErrorReporter *) override {
    std::abort();
  }
  int removeErrorReporter(Presonus::UC::INetworkErrorReporter *) override {
    std::abort();
  }
  int simulateConnectionErrors() override { std::abort(); }
  int waitForOutgoingEvents(int) override { std::abort(); }
  int suspendNetworkAdapters(unsigned char) override { std::abort(); }
  int isSendingFromExternalConnection(int) override { std::abort(); }
  struct Client {
    int id, external;
    std::string text;
  };
  std::vector<Client> clients;
  std::vector<long long> trace;
  MeterManagerBase *manager = nullptr;
  bool available = true, has = true;
  unsigned int session = 0;
  int limit = 1, ticks = 0;
  bool serverAvailable() const override { return available; }
  int clientCount() const override { return static_cast<int>(clients.size()); }
  presonus::meter::ClientView clientAt(int i) const override {
    const auto &c = clients.at(i);
    return {c.id, c.external != 0, c.text.c_str()};
  }
  bool hasClients() const override {
    const_cast<Env *>(this)->trace.push_back(6);
    return has;
  }
  std::uint32_t sessionId() const override { return session; }
  int sendEvent(const Presonus::UC::Event &e, int flag) override {
    trace.insert(trace.end(), {8, e.routeA, e.routeB, flag});
    return 1;
  }
  void tick(bool phase) override {
    trace.insert(trace.end(), {5, phase});
    if (++ticks >= limit)
      manager->sourcePortStop = true;
  }
  void clientTick(bool phase) override {
    trace.insert(trace.end(), {7, phase});
  }
};
struct Manager final : MeterManagerBase {
  Env &env;
  bool joined = true;
  explicit Manager(Env &e) : MeterManagerBase(&e, e), env(e) {
    e.manager = this;
  }
  void sourcePortStart() override { env.trace.push_back(1); }
  bool sourcePortJoin(unsigned int ms) override {
    env.trace.insert(env.trace.end(), {2, ms});
    return joined;
  }
  void sourcePortTerminate() override { env.trace.push_back(3); }
  void sourcePortSleep(unsigned int ms) override {
    env.trace.insert(env.trace.end(), {4, ms});
  }
};
int main() {
  // Actual pinned CCL provider smoke, separate from boundary-stub differential
  // observations: startup and shutdown must complete with a real OS thread.
  {
    Env providerEnvironment;
    MeterManagerBase providerManager(&providerEnvironment, providerEnvironment);
    providerEnvironment.manager = &providerManager;
    providerManager.sourcePortStop = true;
    providerManager.startup();
    providerManager.shutdown();
    if (!providerManager.sourcePortStop ||
        providerManager.sourcePortRunning != 0)
      return 4;
  }
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    int method, a, b, c, d, n;
    if (!(in >> method >> a >> b >> c >> d >> n))
      return 2;
    Env env;
    Manager manager(env);
    env.available = a != 0;
    env.has = b != 0;
    env.limit = c;
    manager.sourcePortRunning = static_cast<unsigned char>(d);
    std::vector<long long> result;
    if (method == 1)
      manager.startup();
    else if (method == 2) {
      manager.joined = b != 0;
      manager.shutdown();
      result.push_back(manager.sourcePortStop);
    } else if (method == 3) {
      manager.sourcePortStop = n != 0;
      result.push_back(manager.threadEntry());
      result.push_back(manager.sourcePortRunning);
      result.push_back(manager.sourcePortStop);
    } else if (method == 4) {
      for (int i = 0; i < n; ++i) {
        Env::Client client;
        in >> client.id >> client.external >> client.text;
        if (client.text == "_")
          client.text.clear();
        env.clients.push_back(client);
      }
      for (auto &list : manager.sourcePortClients)
        list.add(-777);
      manager.updateClients();
      for (auto &list : manager.sourcePortClients) {
        result.push_back(list.count());
        for (int i = 0; i < list.count(); ++i)
          result.push_back(list.at(i));
      }
    } else if (method == 5) {
      env.session = static_cast<unsigned int>(a);
      Presonus::UC::Event event;
      event.routeA = static_cast<unsigned int>(b);
      event.routeB = static_cast<unsigned int>(c);
      Core::FixedSizeVector<int, 100> clients;
      for (int i = 0, id; i < n; ++i) {
        in >> id;
        clients.add(id);
      }
      manager.sendToClients(clients, event);
      result.insert(result.end(), {event.routeA, event.routeB});
    } else
      return 3;
    result.insert(result.end(), env.trace.begin(), env.trace.end());
    std::cout << '[';
    for (std::size_t i = 0; i < result.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << result[i];
    }
    std::cout << "]\n";
  }
}
