#pragma once
#include "presonus/uc/network_manager_services.hpp"
#include <stdexcept>
// Fixture-only completion of unrelated pure slots. Every unsupported call fails
// loudly. These are not original service implementations or production ports.
class FixtureManager final : public Presonus::UC::NetworkManager {
  [[noreturn]] static int unsupported() {
    throw std::logic_error("unsupported network fixture slot");
  }

public:
  using NetworkManager::NetworkManager;
  int startup(unsigned char) override { return unsupported(); }
  int shutdown() override { return unsupported(); }
  int setPortNumber(unsigned short, unsigned short, int) override {
    return unsupported();
  }
  int setLocalName(const char *) override { return unsupported(); }
  int setNetworkPriority(int) override { return unsupported(); }
  int registerListener(Presonus::UC::INetworkListener *) override {
    return unsupported();
  }
  int unregisterListener(Presonus::UC::INetworkListener *) override {
    return unsupported();
  }
  int registerServer(int &, Presonus::UC::IEventHandler *,
                     const Presonus::UC::ServerInfo &, int) override {
    return unsupported();
  }
  int unregisterServer(Presonus::UC::IEventHandler *) override {
    return unsupported();
  }
  int updateServer(Presonus::UC::IEventHandler *) override {
    return unsupported();
  }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const Presonus::UC::ServerInfo &) override {
    return unsupported();
  }
  int removeRemoteServer(int) override { return unsupported(); }
  int sendMulticastEvent(const Presonus::UC::Event &) override {
    return unsupported();
  }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    return unsupported();
  }
  int processIdle() override { return unsupported(); }
  int getServerContextInfo(Presonus::UC::ServerContextInfo &, int) override {
    return unsupported();
  }
  int addExternalConnection(Presonus::UC::IConnection *&,
                            Presonus::UC::IDataChannel *, int, unsigned char,
                            Presonus::UC::IEventHandler *) override {
    return unsupported();
  }
  int updateExternalConnection(Presonus::UC::IDataChannel *, int) override {
    return unsupported();
  }
  int removeExternalConnection(Presonus::UC::IDataChannel *) override {
    return unsupported();
  }
  int rescanAll(unsigned char) override { return unsupported(); }
  int resetConnection() override { return unsupported(); }
  int addErrorReporter(Presonus::UC::INetworkErrorReporter *) override {
    return unsupported();
  }
  int removeErrorReporter(Presonus::UC::INetworkErrorReporter *) override {
    return unsupported();
  }
  int simulateConnectionErrors() override { return unsupported(); }
  int waitForOutgoingEvents(int) override { return unsupported(); }
  int suspendNetworkAdapters(unsigned char) override { return unsupported(); }
  int isSendingFromExternalConnection(int) override { return unsupported(); }
  void onServerAdded(void *,
                     const Presonus::UC::DiscoveryDescriptor &) override {
    unsupported();
  }
  void onServerRemoved(void *) override { unsupported(); }
  void onConnectionError(Presonus::UC::Connection *, bool) override {
    unsupported();
  }
};
