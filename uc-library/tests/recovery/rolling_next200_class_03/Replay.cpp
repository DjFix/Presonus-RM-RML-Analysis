#include "presonus/MeterManagerBase.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {
struct UnusedServices final : presonus::meter::Environment,
                              Presonus::UC::INetworkManager {
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
  int sendEvent(const Presonus::UC::Event &, int) override { std::abort(); }
  bool serverAvailable() const override { std::abort(); }
  int clientCount() const override { std::abort(); }
  presonus::meter::ClientView clientAt(int) const override { std::abort(); }
  bool hasClients() const override { std::abort(); }
  std::uint32_t sessionId() const override { std::abort(); }
  void tick(bool) override { std::abort(); }
  void clientTick(bool) override { std::abort(); }
};

struct MeterManagerProbe : Presonus::MeterManagerBase {
  explicit MeterManagerProbe(UnusedServices &services)
      : MeterManagerBase(&services, services) {}
  using MeterManagerBase::sendUCNETMeters;

  void processMeters(bool) override { std::abort(); }
  void sourcePortStart() override { std::abort(); }
  bool sourcePortJoin(unsigned int) override { std::abort(); }
  void sourcePortTerminate() override { std::abort(); }
  void sourcePortSleep(unsigned int) override { std::abort(); }
};
} // namespace

int main() {
  int state;
  bool flag;
  while (std::cin >> state >> flag) {
    UnusedServices services;
    MeterManagerProbe manager(services);
    manager.sourcePortRunning = 11 + state;
    manager.sourcePortStop = state % 2 != 0;
    for (auto &clients : manager.sourcePortClients) {
      for (int index = 0; index < state; ++index)
        clients.add(100 + index);
    }
    unsigned char before[sizeof(manager)];
    std::memcpy(before, &manager, sizeof(manager));
    manager.sendUCNETMeters(flag);
    std::cout << (std::memcmp(before, &manager, sizeof(manager)) == 0) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
