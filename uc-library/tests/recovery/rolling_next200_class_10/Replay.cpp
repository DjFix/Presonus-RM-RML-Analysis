#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/uc/NetworkItem.hpp"

#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {
using Core::Portable::Component;
using Presonus::UC::NetworkItem;

[[noreturn]] void unexpectedCall() {
  throw std::logic_error("onServerChanged called an application boundary");
}

class UnusedDependencies final
    : public presonus::surface::SurfaceNetworkDependencies {
public:
  int kind(const NetworkItem &) const override { unexpectedCall(); }
  NetworkItem *associatedItem(const NetworkItem &) const override {
    unexpectedCall();
  }
  void title(const NetworkItem &, Core::CStringBuffer<128> &) const override {
    unexpectedCall();
  }
  const char *host(const NetworkItem &) const override { unexpectedCall(); }
  int mappingCount() const override { unexpectedCall(); }
  const char *mappingName(int) const override { unexpectedCall(); }
  int targetType() const override { unexpectedCall(); }
  bool stored(const char *, NetworkItem *) const override { unexpectedCall(); }
  void acquire(NetworkItem *) override { unexpectedCall(); }
  void release(NetworkItem *, bool) override { unexpectedCall(); }
  void *component(NetworkItem *) override { unexpectedCall(); }
  void *mixerCast(void *) override { unexpectedCall(); }
  void *dawCast(void *) override { unexpectedCall(); }
  void setMixer(void *) override { unexpectedCall(); }
  void setDAW(void *) override { unexpectedCall(); }
  void setTransport(void *) override { unexpectedCall(); }
  void itemInfo(int, NetworkItem *) override { unexpectedCall(); }
  void storeSelected(const char *, NetworkItem *, int) override {
    unexpectedCall();
  }
  void setNetworkRoot(Component *) override { unexpectedCall(); }
  void selectModelItem(NetworkItem *) override { unexpectedCall(); }
  int wiredAssignMode() const override { unexpectedCall(); }
  void configureNetwork(const char *) override { unexpectedCall(); }
  void resumeAdaptors() override { unexpectedCall(); }
  void enableNetwork(bool) override { unexpectedCall(); }
  void setupLocalIP() override { unexpectedCall(); }
};

class UnusedNetwork final : public presonus::surface::SurfaceNetworkProvider {
public:
  int localAddresses(Core::Sockets::IPAddress *, int) const override {
    unexpectedCall();
  }
  bool parseAddress(Core::Sockets::SocketAddress &,
                    const char *) const override {
    unexpectedCall();
  }
};

void replay(bool hasItem, bool populated) {
  Component parameters;
  UnusedDependencies dependencies;
  UnusedNetwork network;
  Presonus::DelayTimer timer(0);
  NetworkItem item(&parameters);
  item.setPortableIdentity("server");
  presonus::surface::SurfaceNetworkState state{
      parameters, dependencies, network, timer, {}, {}};
  if (populated) {
    state.mixers.add(&item);
    state.daws.add(&item);
    state.selectedMixer = &item;
    state.selectedDAW = &item;
    state.selectedMidiMapping = 7;
    state.adaptorConfigPending = true;
  }
  Presonus::Surface::NetworkSetupComponent component(state);
  unsigned char beforeState[sizeof(state)], beforeComponent[sizeof(component)],
      beforeItem[sizeof(item)];
  std::memcpy(beforeState, &state, sizeof(state));
  std::memcpy(beforeComponent, &component, sizeof(component));
  std::memcpy(beforeItem, &item, sizeof(item));
  component.onServerChanged(hasItem ? &item : nullptr);
  const bool bytesPreserved =
      std::memcmp(beforeState, &state, sizeof(state)) == 0 &&
      std::memcmp(beforeComponent, &component, sizeof(component)) == 0 &&
      std::memcmp(beforeItem, &item, sizeof(item)) == 0;
  const bool statePreserved =
      bytesPreserved && state.mixers.count() == int(populated) &&
      state.daws.count() == int(populated) &&
      (!populated || (state.mixers[0] == &item && state.daws[0] == &item)) &&
      std::strcmp(item.portableIdentity().str(), "server") == 0;
  std::cout << statePreserved << '\n';
}
} // namespace

int main() {
  int hasItem, populated;
  while (std::cin >> hasItem >> populated)
    replay(hasItem != 0, populated != 0);
}
