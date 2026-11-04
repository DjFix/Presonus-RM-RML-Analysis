#include "presonus/avb/AvbComponent.hpp"
#include "presonus/avb/SurfaceAvbComponent.hpp"
#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
struct Item {
  int kind;
  Presonus::UC::NetworkItem *associated;
};
struct MockListenerServices : presonus::avb::ListenerServices {
  using Listener = presonus::avb::Listener;
  using RoutingPacket = presonus::avb::RoutingPacket;
  Listener *addListener(unsigned long long, unsigned short,
                        unsigned char) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void removeListener(Listener *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setAudioClockToListener(Listener *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void configureStaticTalkerStreams() override {
    throw std::runtime_error("unexpected test boundary");
  }
  void routeLinkSlotsFromAvb() override {
    throw std::runtime_error("unexpected test boundary");
  }
  void sendRoutingPacket(const RoutingPacket &) override {
    throw std::runtime_error("unexpected test boundary");
  }
};
struct MockNetworkSetupServices : presonus::mixer::NetworkSetupServices {
  int itemKind(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  int itemFilter(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  const char *itemName(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  const char *itemSerial(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  void itemTitle(const Presonus::UC::NetworkItem &,
                 Core::CStringBuffer<128> &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  Presonus::UC::ClientRootComponent *
  component(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  Presonus::UC::ClientImplementation &
  eventSender(Presonus::UC::ClientRootComponent &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  void acquire(Presonus::UC::NetworkItem &) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void release(Presonus::UC::NetworkItem &, bool) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void *mixerForClient(Presonus::UC::ClientRootComponent &) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setRemoteMixer(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void remoteIdle() override {
    throw std::runtime_error("unexpected test boundary");
  }
  void restoredSelection() override {
    throw std::runtime_error("unexpected test boundary");
  }
  void serverParamChanged(Core::Portable::Parameter *, int) override {
    throw std::runtime_error("unexpected test boundary");
  }
};
struct MockSurfaceNetworkDependencies
    : presonus::surface::SurfaceNetworkDependencies {
  int kind(const Presonus::UC::NetworkItem &item) const override {
    return reinterpret_cast<const Item &>(item).kind;
  }
  Presonus::UC::NetworkItem *
  associatedItem(const Presonus::UC::NetworkItem &item) const override {
    return reinterpret_cast<const Item &>(item).associated;
  }
  void title(const Presonus::UC::NetworkItem &,
             Core::CStringBuffer<128> &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  const char *host(const Presonus::UC::NetworkItem &) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  int mappingCount() const override {
    throw std::runtime_error("unexpected test boundary");
  }
  const char *mappingName(int) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  int targetType() const override {
    throw std::runtime_error("unexpected test boundary");
  }
  bool stored(const char *, Presonus::UC::NetworkItem *) const override {
    throw std::runtime_error("unexpected test boundary");
  }
  void acquire(Presonus::UC::NetworkItem *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void release(Presonus::UC::NetworkItem *, bool) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void *component(Presonus::UC::NetworkItem *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void *mixerCast(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void *dawCast(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setMixer(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setDAW(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setTransport(void *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void itemInfo(int, Presonus::UC::NetworkItem *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void storeSelected(const char *, Presonus::UC::NetworkItem *, int) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setNetworkRoot(Core::Portable::Component *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void selectModelItem(Presonus::UC::NetworkItem *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  int wiredAssignMode() const override {
    throw std::runtime_error("unexpected test boundary");
  }
  void configureNetwork(const char *) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void resumeAdaptors() override {
    throw std::runtime_error("unexpected test boundary");
  }
  void enableNetwork(bool) override {
    throw std::runtime_error("unexpected test boundary");
  }
  void setupLocalIP() override {
    throw std::runtime_error("unexpected test boundary");
  }
};
struct Child : Core::Portable::Component {
  int &count;
  explicit Child(int &c) : count(c) {}
  ~Child() override { ++count; }
};
extern "C" void destroyBase(Presonus::AVB::SurfaceAvbComponent *) asm(
    "_ZN8Presonus3AVB19SurfaceAvbComponentD2Ev");
extern "C" void destroyComplete(Presonus::AVB::SurfaceAvbComponent *) asm(
    "_ZN8Presonus3AVB19SurfaceAvbComponentD1Ev");
int main() {
  int op, mask, a, b, c, d, x, alias;
  while (std::cin >> op >> mask >> a >> b >> c >> d >> x >> alias) {
    presonus::avb::Listener ls[4]{{static_cast<std::uint8_t>(a)},
                                  {static_cast<std::uint8_t>(b)},
                                  {static_cast<std::uint8_t>(c)},
                                  {static_cast<std::uint8_t>(d)}};
    presonus::avb::ListenerState st;
    st.cascade = mask & 1 ? ls : nullptr;
    st.mixer = mask & 2 ? ls + 1 : nullptr;
    st.csInput = mask & 4 ? ls + 2 : nullptr;
    st.console = mask & 8 ? ls + 3 : nullptr;
    MockListenerServices svc;
    Presonus::AVB::AvbComponent avb(st, svc);
    int l = 111, ch = 222, *cp = alias ? &l : &ch, r = 0;
    if (op == 1)
      r = avb.getConsoleTalkbackListenerAndChannel(&l, cp);
    if (op == 2)
      r = avb.getCSTalkbackListenerAndChannel(&l, cp);
    if (op == 3)
      r = avb.getListenerAndChannelForInput(&l, cp, x, mask & 1);
    if (op == 4)
      r = avb.getTalkerAndChannelForInput(&l, cp, x);
    if (op <= 4)
      std::cout << r << ' ' << l << ' ' << *cp;
    else if (op == 5)
      std::cout << avb.hasListeners();
    else if (op == 6)
      std::cout << avb.getAVBListenerIndex(x);
    else if (op == 7 || op == 8) {
      int destroyed = 0;
      void *storage =
          ::operator new(sizeof(Presonus::AVB::SurfaceAvbComponent));
      auto *component = new (storage) Presonus::AVB::SurfaceAvbComponent;
      component->addChild(new Child(destroyed));
      if (op == 7)
        destroyBase(component);
      else
        destroyComplete(component);
      ::operator delete(storage);
      std::cout << destroyed;
    } else if (op == 9) {
      Core::Portable::Component params;
      MockNetworkSetupServices services;
      presonus::mixer::NetworkSetupState state{params, services};
      Presonus::Mixer::NetworkSetupComponent component(state);
      auto ptr = reinterpret_cast<Presonus::Mixer::AVBRemoteMixerHandler *>(
          static_cast<std::uintptr_t>(a));
      component.setMixerHandler(ptr);
      std::cout << reinterpret_cast<std::uintptr_t>(state.mixerHandler) << ' '
                << state.hasRemoteHandler;
    } else if (op == 10) {
      Core::Portable::Component params;
      MockSurfaceNetworkDependencies dep;
      presonus::surface::SurfaceNetworkProvider net;
      Presonus::DelayTimer timer(0);
      presonus::surface::SurfaceNetworkState state{params, dep, net, timer};
      Item target{a, nullptr}, unrelated{0, nullptr}, entries[3]{};
      auto item = reinterpret_cast<Presonus::UC::NetworkItem *>(&target);
      for (int j = 0; j < b; ++j) {
        entries[j].associated =
            j == c ? item
                   : reinterpret_cast<Presonus::UC::NetworkItem *>(&unrelated);
        state.mixers.add(
            reinterpret_cast<Presonus::UC::NetworkItem *>(&entries[j]));
      }
      Presonus::Surface::NetworkSetupComponent component(state);
      std::cout << component.isSlaveItem(item);
    }
    std::cout << '\n';
  }
}
