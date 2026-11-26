#include "presonus/MeterManager.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#undef NDEBUG
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Presonus;
using namespace Presonus::UC;
namespace presonus::meter {
struct MeterStateAccess {
  static bool mode(const MeterBallistics &m) { return m.state_.mode; }
};
} // namespace presonus::meter
struct Env final : presonus::meter::Environment {
  int clientCount() const override { return 0; }
  presonus::meter::ClientView clientAt(int) const override { std::abort(); }
  bool hasClients() const override { return false; }
  std::uint32_t sessionId() const override { return 42; }
  void tick(bool) override {}
  void clientTick(bool) override {}
};
struct ConnectionObserver final : UC::BasicConnection {
  using UC::BasicConnection::BasicConnection;
  int calls = 0;
  const UC::Event *identity = nullptr;
  bool result = false;
  bool sendEvent(const UC::Event &event) override {
    ++calls;
    identity = &event;
    assert(event.routeA == 0 && event.routeB == 0);
    return result = UC::BasicConnection::sendEvent(event);
  }
};
struct Network final : UC::INetworkManager {
  UC::EventFactory &factory;
  ConnectionObserver *external = nullptr;
  std::vector<std::vector<unsigned>> traces;
  explicit Network(UC::EventFactory &f) : factory(f) {}
  int handleEvent(void *, const UC::Event &) override { std::abort(); }
  int sendEvent(const UC::Event &e, int flag) override {
    assert(flag == 1);
    assert(external && external->calls == 1);
    char wire[4096]{};
    assert(factory.write(wire, sizeof wire, e) > 0);
    // The registered typed codec serializes the live independent envelope.
    traces.push_back({e.type, e.reserved04, e.routeA, e.routeB});
    for (int i = 6; i < 21; ++i)
      traces.back().push_back(static_cast<unsigned char>(wire[i]));
    return 0;
  }
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
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string action = argv[1];
  presonus::uc::CclFactoryRegistry registry;
  presonus::uc::Meter8FactoryCodec codec8;
  presonus::uc::Meter16FactoryCodec codec16;
  codec8.registerIn(registry.registry());
  codec16.registerIn(registry.registry());
  UC::EventFactory factory(registry.registry());
  Network net(factory);
  Env env;
  if (action == "roster") {
    int index = std::stoi(argv[2]), selector = std::stoi(argv[3]),
        kind = std::stoi(argv[4]);
    std::string pop = argv[5];
    presonus::meter::ManagerRosters r;
    r.word1564 = 1;
    r.word156c = 1;
    r.word1570 = 2;
    r.word1574 = 1;
    r.word1578 = 2;
    std::vector<MeterMaid *> before;
    for (auto *v : {&r.primary, &r.sections, &r.secondary})
      if (pop != "empty")
        for (int i = 0; i < 4; ++i) {
          auto *p = pop == "null" ? nullptr : new MeterMaid;
          v->add(p);
          if (p)
            before.push_back(p);
        }
    MeterManager m(presonus::meter::ManagerSourcePortTag{}, &env, net, r);
    auto *p = m.getMeterMaid(index, selector, kind);
    bool allocated = true;
    for (auto *old : before)
      if (old == p)
        allocated = false;
    int roster = -1, position = -1, j = 0;
    for (auto *v : {&r.primary, &r.sections, &r.secondary}) {
      for (int i = 0; i < v->count(); ++i)
        if (v->at(i) == p) {
          roster = j;
          position = i;
        }
      ++j;
    }
    std::cout << roster << " " << r.primary.count() << " " << r.sections.count()
              << " " << r.secondary.count() << " " << allocated << " "
              << position << " " << presonus::meter::MeterStateAccess::mode(*p)
              << "\n";
  } else if (action == "external" || action == "negative") {
    int count = std::stoi(argv[2]), selector = std::stoi(argv[3]),
        width = std::stoi(argv[4]);
    int result = argc > 5 ? std::stoi(argv[5]) : 1;
    presonus::uc::BasicConnectionTypedValues values;
    presonus::uc::BasicConnectionProviderScope providers(factory, values);
    ConnectionObserver external(0);
    net.external = &external;
    presonus::meter::MutableMeterOrigins mutableOrigins;
    auto a = std::make_shared<UC::MeterEvent8>();
    auto b = std::make_shared<UC::MeterEvent16>();
    a->header = {19778, 1268, 44, 55};
    b->header = {19795, 2292, 44, 55};
    a->keyBits = b->keyBits = 0x12345678;
    presonus::uc::EventOrigins origins;
    auto origin8 = origins.bind(*a);
    auto origin16 = origins.bind(*b);
    mutableOrigins.bind(a);
    mutableOrigins.bind(b);
    codec8.bind(*a);
    codec16.bind(*b);
    auto &header = width == 1 ? a->header : b->header;
    auto view = *origins.meter(&header);
    MeterManagerBase m(presonus::meter::ExternalTransportTag{}, &env, net,
                       external, mutableOrigins, codec8);
    Core::FixedSizeVector<int, 100> clients;
    for (int i = 0; i < count; ++i)
      clients.add(i == 0 ? 7 : i == 1 ? 11 : 19);
    if (action == "negative") {
      mutableOrigins.unbind(header);
      bool rejected = false;
      try {
        m.sendToExternalClients(clients, view, selector);
      } catch (const std::invalid_argument &) {
        rejected = true;
      }
      assert(rejected);
      mutableOrigins.bind(a);
      mutableOrigins.bind(b);
      view.data = nullptr;
      rejected = false;
      try {
        m.sendToExternalClients(clients, view, selector);
      } catch (const std::invalid_argument &) {
        rejected = true;
      }
      assert(rejected);
      std::weak_ptr<UC::MeterEvent8> weak = a;
      auto *h = &a->header;
      a.reset();
      assert(!weak.expired());
      mutableOrigins.unbind(*h);
      assert(weak.expired());
      std::cout << "negative-pass\n";
      return 0;
    }
    if (!result) {
      if (width == 1)
        codec8.unbind(*a);
      else
        codec16.unbind(*b);
    }
    m.sendToExternalClients(clients, view, selector);
    assert(external.calls == (count ? 1 : 0));
    if (count)
      assert(external.identity == &header && external.result == bool(result));
    auto *item = presonus::uc::BasicConnectionSourceAccess::queue(external)
                     .retrieveEvent();
    std::cout << header.routeA << " " << header.routeB << " " << (item ? 1 : 0)
              << " " << net.traces.size();
    if (item) {
      assert(item->getData().routeA == 0 && item->getData().routeB == 0);
      if (width == 1)
        assert(dynamic_cast<presonus::uc::TypedEventItem<UC::MeterEvent8> *>(
            item));
      else
        assert(dynamic_cast<presonus::uc::TypedEventItem<UC::MeterEvent16> *>(
            item));
      delete item;
    }
    for (auto &t : net.traces)
      for (auto n : t)
        std::cout << " " << n;
    std::cout << "\n";
    codec8.unbind(*a);
    codec16.unbind(*b);
  } else if (action == "noop") {
    presonus::meter::ManagerRosters r;
    MeterManager m(presonus::meter::ManagerSourcePortTag{}, &env, net, r);
    Core::Property p(0x12345678, 8);
    m.getProperty(p);
    m.release();
    std::cout << "noop-pass\n";
  } else
    return 2;
}
