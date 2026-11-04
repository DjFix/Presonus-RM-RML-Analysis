#include "presonus/MeterControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/reconstruction200/large02_w08.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
using namespace Core::Portable;
using namespace Presonus;
static void *watched = nullptr;
static int releases = 0, deallocations = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    ++deallocations;
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  if (p == watched)
    ++deallocations;
  __real__ZdlPvm(p, n);
}
struct Scale : Core::Interpolator {
  ~Scale() override { ++releases; }
};
struct P : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
struct Pan : PanControl {
  using PanControl::PanControl;
  int invalidations = 0;
  void invalidate(const Core::Rect &) override { ++invalidations; }
};
struct Meter : MeterControl {
  using MeterControl::MeterControl;
  float current() const { return value; }
  int zeros() const {
    return !interpolator + !peakParameter + !reverse + !immediate + !hidePeak +
           (value == 0) + (drawnValue == 0) + (peak == 0) + (drawnPeak == 0) +
           (valueDirty == Core::Rect()) + (peakDirty == Core::Rect());
  }
};
struct Mute : Surface::MuteGroupsComponent {
  void add(Parameter *p) { paramList.add(p); }
};
struct Controller : ViewController {
  std::array<P *, 3> p;
  Controller(P *a, P *b, P *c) : p{a, b, c} {}
  void *castTo(Core::InterfaceID) override { return nullptr; }
  View *createView(const char *) override { return nullptr; }
  void *getObjectForView(const char *name, const char *) override {
    if (!std::strcmp(name, "l"))
      return p[0];
    if (!std::strcmp(name, "s"))
      return p[1];
    if (!std::strcmp(name, "c"))
      return p[2];
    return nullptr;
  }
};

// Test network boundary only. Production goes through actual
// ClientImplementation routing and actual CCL serialization/parse; no network
// is opened.
namespace UCFixture {
using namespace Presonus::UC;
struct Network : INetworkManager {
  presonus::uc::ClientTypedOrigins &origins;
  int sends = 0, index = 0, valid = 0;
  explicit Network(presonus::uc::ClientTypedOrigins &o) : origins(o) {}
  int handleEvent(void *, const Event &) override { return 0; }
  int sendEvent(const Event &event, int) override {
    auto *message = origins.get<MessageEvent>(&event);
    if (!message)
      std::abort();
    MessageAttributes attributes(*message);
    ++sends;
    index = attributes.getInt("presetMuteGroupIndex");
    valid = event.type == 0x4a4d && event.routeA == 11 && event.routeB == 22 &&
            attributes.getID() &&
            !std::strcmp(attributes.getID(), "presetMuteGroup") &&
            attributes.getURL() &&
            !std::strcmp(attributes.getURL(), "mutegroup");
    return 1;
  }
  int startup(unsigned char) override { return 0; }
  int shutdown() override { return 0; }
  int setPortNumber(unsigned short, unsigned short, int) override { return 0; }
  int setLocalName(const char *) override { return 0; }
  int setNetworkPriority(int) override { return 0; }
  int registerListener(INetworkListener *) override { return 0; }
  int unregisterListener(INetworkListener *) override { return 0; }
  int registerServer(int &, IEventHandler *, const ServerInfo &, int) override {
    return 0;
  }
  int unregisterServer(IEventHandler *) override { return 0; }
  int updateServer(IEventHandler *) override { return 0; }
  int addRemoteServer(int &, const char *, unsigned short, unsigned short, int,
                      const ServerInfo &) override {
    return 0;
  }
  int removeRemoteServer(int) override { return 0; }
  int registerHandler(int &, IEventHandler *) override { return 0; }
  int unregisterHandler(IEventHandler *) override { return 0; }
  int sendMulticastEvent(const Event &) override { return 0; }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    return 0;
  }
  int processIdle() override { return 0; }
  int getServerContextInfo(ServerContextInfo &, int) override { return 0; }
  int addExternalConnection(IConnection *&, IDataChannel *, int, unsigned char,
                            IEventHandler *) override {
    return 0;
  }
  int updateExternalConnection(IDataChannel *, int) override { return 0; }
  int removeExternalConnection(IDataChannel *) override { return 0; }
  int rescanAll(unsigned char) override { return 0; }
  int resetConnection() override { return 0; }
  int addErrorReporter(INetworkErrorReporter *) override { return 0; }
  int removeErrorReporter(INetworkErrorReporter *) override { return 0; }
  int simulateConnectionErrors() override { return 0; }
  int waitForOutgoingEvents(int) override { return 0; }
  int suspendNetworkAdapters(unsigned char) override { return 0; }
  int isSendingFromExternalConnection(int) override { return 0; }
};
struct Client : ClientImplementation {
  explicit Client(Network &n)
      : ClientImplementation(presonus::uc::ClientStatePortTag{}, n, 11, 22) {}
  std::uint64_t getSystemTime() const override { return 0; }
  void updateLevels(const MeterEvent &) override {}
  void receiveEvent(const TimeCodeEvent &) override {}
  void receiveEvent(const ParamEvent &) override {}
  void receiveEvent(const MessageEvent &) override {}
  void receiveEvent(const BinaryEvent &) override {}
  void receiveEvent(const DebugEvent &) override {}
  void sendAllToServer() override {}
};
} // namespace UCFixture

int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  int op = std::atoi(argv[1]);
  auto arg = [&](int i) { return i < argc ? std::atoi(argv[i]) : 0; };
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.maxValue = 1;
  if (op == 2 || op == 3 || op == 4 || op == 5 || op == 9) {
    P a(info), b(info);
    Pan p(Core::Rect(2, 3, 42, 53), nullptr);
    using Setter = void (PanControl::*)(Parameter *);
    Setter setter = op == 2   ? &PanControl::setStereoParam
                    : op == 3 ? &PanControl::setStereoPanParam
                    : op == 4 ? &PanControl::setChannelNumberParam
                    : op == 5 ? &PanControl::setRightSideParam
                              : &PanControl::setLinkParam;
    auto ptr = [&](int n) -> Parameter * {
      return n == 1 ? &a : n == 2 ? &b : nullptr;
    };
    (p.*setter)(ptr(arg(2)));
    p.invalidations = 0;
    (p.*setter)(ptr(arg(3)));
    const int idx = op == 2 ? 0 : op == 3 ? 4 : op == 4 ? 2 : op == 5 ? 3 : 1;
    auto v = p.panParameters()[idx];
    std::cout << (v == &a   ? 1
                  : v == &b ? 2
                            : 0)
              << ' ' << a.observers() << ' ' << b.observers() << ' '
              << p.invalidations << '\n';
    (p.*setter)(nullptr);
    return 0;
  }
  if (op == 1 || op == 10) {
    MeterScaleControl p(Core::Rect(2, 3, 42, 53));
    std::cout << !p.hasScaleInterpolator() << ' ' << (p.scaleState() == 0)
              << '\n';
    return 0;
  }
  if (op == 6 || op == 7 || op == 14) {
    auto *p = new MeterScaleControl(Core::Rect());
    if (arg(2))
      p->adoptScaleInterpolator(std::make_unique<Scale>());
    watched = p;
    if (op == 7)
      delete p;
    else {
      p->~MeterScaleControl();
      __real__ZdlPv(p);
    }
    watched = nullptr;
    std::cout << releases << ' ' << deallocations << '\n';
    return 0;
  }
  if (op == 11 || op == 12) {
    Pan p(Core::Rect(2, 3, 42, 53), nullptr);
    int zero = 0;
    for (auto *v : p.panParameters())
      zero += v == nullptr;
    std::cout << zero << ' ' << (p.getParameter() == nullptr) << '\n';
    return 0;
  }
  if (op == 13 || op == 15) {
    Meter p(Core::Rect(2, 3, 42, 53));
    std::cout << p.zeros() << '\n';
    return 0;
  }
  if (op == 8) {
    P p(info);
    p.setValue(arg(2) / 100.f);
    Meter c{Core::Rect()};
    c.connect(arg(3) ? &p : nullptr);
    std::cout << (c.getParameter() != nullptr) << ' ' << int(c.current() * 100)
              << '\n';
    return 0;
  }
  if (op == 18) {
    P l(info), s(info), c(info);
    Controller controller(&l, &s, &c);
    Pan p(Core::Rect(), nullptr);
    if (arg(2))
      p.bindPanController(&controller);
    Attributes a(AttributeAllocator::getDefault());
    if (arg(3)) {
      a.set("link", "l");
      a.set("isstereo", "s");
      a.set("chnum", "c");
    }
    a.set("valueBarWidth", arg(4));
    p.setAttributes(a);
    std::cout << (p.panParameters()[1] == &l) << ' '
              << (p.panParameters()[0] == &s) << ' '
              << (p.panParameters()[2] == &c) << ' ' << p.panValueBarWidth()
              << ' ' << (p.getImage().isValid()) << '\n';
    p.setLinkParam(nullptr);
    p.setStereoParam(nullptr);
    p.setChannelNumberParam(nullptr);
    return 0;
  }
  if (op == 16 || op == 17 || op == 19) {
    presonus::uc::ClientTypedOrigins origins;
    UCFixture::Network network(origins);
    UCFixture::Client client(network);
    Mute m;
    if (arg(6))
      m.bindMuteClient(&client, &origins);
    ParamInfo pi = info;
    pi.tag = arg(2);
    auto *p = new P(*new ParamInfo(pi), true);
    p->setValue(arg(4) / 100.f);
    m.add(p);
    pi.tag = pi.tag < 8 ? pi.tag + 8 : pi.tag - 8;
    auto *q = new P(*new ParamInfo(pi), true);
    q->setValue(.25f);
    m.add(q);
    DelayTimer timer(1.f);
    presonus::timing::DelayTimerAccess::set(
        timer, {0, 1000, 0, 0.001f, bool(arg(5) && arg(2) < 8)});
    std::vector<DelayTimer *> timers(8, nullptr);
    if (arg(2) >= 0 && arg(2) < 8)
      timers[arg(2)] = &timer;
    m.bindMuteTimers(timers);
    if (op == 16)
      m.paramChanged(p, arg(3));
    if (op == 17)
      m.storeMuteGroup(arg(2));
    if (op == 19) {
      presonus::timing::DelayTimerAccess::set(
          timer, {0, 0, 0, 0.f, bool(arg(5) && arg(2) < 8)});
      m.onIdle();
    }
    std::cout << int(p->getValue() * 100) << ' ' << int(q->getValue() * 100)
              << ' ' << timer.isExecuting() << ' '
              << m.muteRefreshTimer().isExecuting();
    if (op == 17 || op == 19)
      std::cout << ' ' << network.sends << ' ' << network.index << ' '
                << network.valid;
    std::cout << '\n';
    return 0;
  }
  return 3;
}
