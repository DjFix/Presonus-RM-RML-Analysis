#include "presonus/mixer/NetworkSetupComponent.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
struct NetworkServices final : presonus::mixer::NetworkSetupServices {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected disconnected network service call");
  }
  int itemKind(const Presonus::UC::NetworkItem &) const override { fail(); }
  int itemFilter(const Presonus::UC::NetworkItem &) const override { fail(); }
  const char *itemName(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  const char *itemSerial(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  void itemTitle(const Presonus::UC::NetworkItem &,
                 Core::CStringBuffer<128> &) const override {
    fail();
  }
  Presonus::UC::ClientRootComponent *
  component(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  Presonus::UC::ClientImplementation &
  eventSender(Presonus::UC::ClientRootComponent &) const override {
    fail();
  }
  void acquire(Presonus::UC::NetworkItem &) override { fail(); }
  void release(Presonus::UC::NetworkItem &, bool) override { fail(); }
  void *mixerForClient(Presonus::UC::ClientRootComponent &) override { fail(); }
  void setRemoteMixer(void *) override { fail(); }
  void remoteIdle() override { fail(); }
  void restoredSelection() override { fail(); }
  void serverParamChanged(Core::Portable::Parameter *, int) override { fail(); }
};

int main() {
  NetworkServices services;
  Core::Portable::Component parameters("network-setup-replay");
  presonus::mixer::NetworkSetupState state{parameters, services, {}};
  Presonus::Mixer::NetworkSetupComponent receiver(state);
  for (unsigned seed = 0; seed < 4; ++seed) {
    for (bool isNull : {false, true}) {
      alignas(void *) std::array<unsigned char, 3> data{
          0x31, static_cast<unsigned char>(seed), 0x79};
      auto *item = reinterpret_cast<Presonus::UC::NetworkItem *>(data.data());
      state.selected = item;
      state.hasRemoteHandler = (seed % 2 != 0);
      receiver.onNetworkItemAcquired(isNull ? nullptr : item);
      const bool changed = state.selected != item ||
                           state.hasRemoteHandler != (seed % 2 != 0) ||
                           state.items.count() != 0;
      std::cout << seed << ' ' << isNull << ' ' << changed;
      for (unsigned byte : data)
        std::cout << ' ' << byte;
      std::cout << '\n';
    }
  }
}
