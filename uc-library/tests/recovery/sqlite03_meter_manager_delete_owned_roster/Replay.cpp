#include "presonus/MeterMaid.hpp"
#include "presonus/MeterManagerBase.hpp"

#include <cstdio>
#include <cstdlib>
#include <string_view>

namespace {
using namespace Presonus;
using namespace Presonus::UC;

class OfflineNetwork final : public INetworkManager {
  int handleEvent(void *, const Event &) override { std::abort(); }
  int startup(unsigned char) override { std::abort(); }
  int shutdown() override { std::abort(); }
  int setPortNumber(unsigned short, unsigned short, int) override {
    std::abort();
  }
  int setLocalName(const char *) override { std::abort(); }
  int setNetworkPriority(int) override { std::abort(); }
  int registerListener(INetworkListener *) override { std::abort(); }
  int unregisterListener(INetworkListener *) override { std::abort(); }
  int registerServer(int &, IEventHandler *, const ServerInfo &, int) override {
    std::abort();
  }
  int unregisterServer(IEventHandler *) override { std::abort(); }
  int updateServer(IEventHandler *) override { std::abort(); }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const ServerInfo &) override {
    std::abort();
  }
  int removeRemoteServer(int) override { std::abort(); }
  int registerHandler(int &, IEventHandler *) override { std::abort(); }
  int unregisterHandler(IEventHandler *) override { std::abort(); }
  int sendEvent(const Event &, int) override { std::abort(); }
  int sendMulticastEvent(const Event &) override { std::abort(); }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    std::abort();
  }
  int processIdle() override { std::abort(); }
  int getServerContextInfo(ServerContextInfo &, int) override { std::abort(); }
  int addExternalConnection(IConnection *&, IDataChannel *, int, unsigned char,
                            IEventHandler *) override {
    std::abort();
  }
  int updateExternalConnection(IDataChannel *, int) override { std::abort(); }
  int removeExternalConnection(IDataChannel *) override { std::abort(); }
  int rescanAll(unsigned char) override { std::abort(); }
  int resetConnection() override { std::abort(); }
  int addErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int removeErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int simulateConnectionErrors() override { std::abort(); }
  int waitForOutgoingEvents(int) override { std::abort(); }
  int suspendNetworkAdapters(unsigned char) override { std::abort(); }
  int isSendingFromExternalConnection(int) override { std::abort(); }
};

class ReplayManager final : public MeterManagerBase {
public:
  explicit ReplayManager(INetworkManager &network)
      : MeterManagerBase(nullptr, network) {}
  using MeterManagerBase::deleteAll;
};

using Roster = Core::Vector<MeterMaid *>;
const void *entries[8]{};
char variants[8]{};
const void *backing = nullptr;
Roster *active = nullptr;
int initialCount = 0;
unsigned derivedDestructions = 0;

class DerivedMeter final : public MeterMaid {
public:
  explicit DerivedMeter(unsigned slot) : slot_(slot) {}
  ~DerivedMeter() override {
    if (!active || active->count() != initialCount ||
        (derivedDestructions & (1u << slot_)))
      std::abort();
    derivedDestructions |= 1u << slot_;
  }

private:
  unsigned slot_;
};

void observeScalarRelease(const void *address) {
  if (!active)
    return;
  for (unsigned slot = 0; slot < 8; ++slot) {
    if (entries[slot] != address)
      continue;
    if (active->count() != initialCount ||
        (variants[slot] == 'g' && !(derivedDestructions & (1u << slot))))
      std::abort();
    std::printf("free:%u\n", slot + 1);
    return;
  }
}

void observeArrayRelease(const void *address) {
  if (active && address == backing)
    std::puts("free-array");
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);

extern "C" void __wrap__ZdlPv(void *address) {
  observeScalarRelease(address);
  __real__ZdlPv(address);
}
extern "C" void __wrap__ZdlPvm(void *address, std::size_t size) {
  observeScalarRelease(address);
  __real__ZdlPvm(address, size);
}
extern "C" void __wrap__ZdaPv(void *address) {
  observeArrayRelease(address);
  __real__ZdaPv(address);
}
extern "C" void __wrap__ZdaPvm(void *address, std::size_t size) {
  observeArrayRelease(address);
  __real__ZdaPvm(address, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 1;
  const std::string_view slots = argv[1];
  const int capacity = std::atoi(argv[2]);
  if (slots.size() > 8 || (capacity != 0 && capacity != 8) ||
      slots.size() > static_cast<unsigned>(capacity))
    return 2;

  OfflineNetwork network;
  ReplayManager manager(network);
  Roster roster(capacity, 4);
  unsigned slot = 0;
  for (char variant : slots) {
    MeterMaid *entry = nullptr;
    if (variant == 'g')
      entry = new DerivedMeter(slot);
    else if (variant == 'b')
      entry = new MeterMaid;
    else if (variant != '0')
      return 3;
    entries[slot] = entry;
    variants[slot] = variant;
    roster.add(entry);
    ++slot;
  }

  active = &roster;
  backing = roster.getItems();
  initialCount = roster.count();
  for (int pass = 0; pass < 2; ++pass) {
    manager.deleteAll(roster);
    if (roster.count() || roster.getCapacity() || roster.getItems() ||
        roster.getDelta() != 4)
      return 4;
    std::puts("clear");
  }
  active = nullptr;
  return 0;
}
