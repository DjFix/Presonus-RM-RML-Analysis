#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/uc/NetworkItem.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {
using Core::Portable::Component;
struct Dependencies : presonus::surface::SurfaceNetworkDependencies {
  int setups = 0;
  int mappingCount() const override { return 0; }
  const char *mappingName(int) const override { return "mapping"; }
  int kind(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {
    throw std::logic_error("unused");
  }
  const char *host(const Presonus::UC::NetworkItem &) const override {
    throw std::logic_error("unused");
  }
  int targetType() const override { return 0; }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    throw std::logic_error("unused");
  }
  void acquire(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void release(Presonus::UC::NetworkItem *, bool) override {
    throw std::logic_error("unused");
  }
  void *component(Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void *mixerCast(void *) override { throw std::logic_error("unused"); }
  void *dawCast(void *) override { throw std::logic_error("unused"); }
  void setMixer(void *) override { throw std::logic_error("unused"); }
  void setDAW(void *) override { throw std::logic_error("unused"); }
  void setTransport(void *) override { throw std::logic_error("unused"); }
  void itemInfo(int, Presonus::UC::NetworkItem *) override {
    throw std::logic_error("unused");
  }
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {
    throw std::logic_error("unused");
  }
  void setNetworkRoot(Component *) override {
    throw std::logic_error("unused");
  }
  void selectModelItem(Presonus::UC::NetworkItem *) override { ++setups; }
  int wiredAssignMode() const override { throw std::logic_error("unused"); }
  void configureNetwork(const char *) override {
    throw std::logic_error("unused");
  }
  void resumeAdaptors() override { throw std::logic_error("unused"); }
  void enableNetwork(bool) override { throw std::logic_error("unused"); }
  void setupLocalIP() override { throw std::logic_error("unused"); }
};

} // namespace

namespace {
template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}
} // namespace

int main() {
  Component parameters;
  Dependencies dependencies;
  presonus::surface::SurfaceNetworkProvider provider;
  Presonus::DelayTimer timer(0);
  presonus::surface::SurfaceNetworkState state{parameters, dependencies,
                                               provider, timer};
  Presonus::Surface::NetworkSetupComponent receiver(state);
  Presonus::UC::NetworkItem pointed(nullptr);
  int value0;
  while (std::cin >> value0) {
    const auto beforeReceiver = snapshot(receiver);
    const auto beforePointed = snapshot(pointed);
    const auto beforeState = snapshot(state);
    const auto beforeParameters = snapshot(parameters);
    const int beforeCallbacks = dependencies.setups;
    receiver.onNetworkItemAcquired(value0 ? &pointed : nullptr);
    std::cout << (beforeReceiver == snapshot(receiver)) << ' '
              << (beforePointed == snapshot(pointed)) << ' '
              << (beforeState == snapshot(state) &&
                  beforeParameters == snapshot(parameters) &&
                  dependencies.setups == beforeCallbacks)
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
