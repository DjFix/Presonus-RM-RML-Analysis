#include "presonus/noaa/ucnet_handler.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <vector>
using namespace Presonus::UC;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::vector<std::string> trace;
static void *endpointAddress, *selfAddress, *spiAllocation;
static PacketQueue *incomingAddress, *outgoingAddress;
static bool capture;
static int allocationCountdown = -1;
static void *packets[32]{};
static unsigned packetCount;
static Presonus::Panel::InputPin *constructedPins[2]{};
static unsigned constructedPinCount;
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t n) {
  if (allocationCountdown == 0) {
    allocationCountdown = -1;
    throw std::bad_alloc();
  }
  if (allocationCountdown > 0)
    --allocationCountdown;
  auto *p = __real__Znwm(n);
  if (capture && n == sizeof(TCardSPI))
    spiAllocation = p;
  if (capture && n == sizeof(Presonus::Panel::InputPin)) {
    assert(constructedPinCount < 2);
    constructedPins[constructedPinCount++] =
        static_cast<Presonus::Panel::InputPin *>(p);
  }
  return p;
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
static void observeDelete(void *p) {
  if (!capture)
    return;
  for (unsigned i = 0; i < packetCount; ++i)
    if (p == packets[i]) {
      trace.push_back("P");
      packets[i] = nullptr;
    }
  for (auto &pin : constructedPins)
    if (p == pin)
      pin = nullptr;
  if (p == spiAllocation) {
    trace.push_back("SPI_DELETE");
    spiAllocation = nullptr;
  }
  if (p == endpointAddress) {
    trace.push_back("E");
    endpointAddress = nullptr;
  }
  if (p == selfAddress) {
    trace.push_back("S");
    selfAddress = nullptr;
  }
}
extern "C" void __wrap__ZdlPv(void *p) {
  observeDelete(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  observeDelete(p);
  __real__ZdlPvm(p, n);
}
extern "C" void
realQueue(PacketQueue *) asm("__real__ZN8Presonus2UC11PacketQueueD2Ev");
extern "C" void
wrapQueue(PacketQueue *p) asm("__wrap__ZN8Presonus2UC11PacketQueueD2Ev");
extern "C" void wrapQueue(PacketQueue *p) {
  if (capture) {
    if (p == outgoingAddress)
      trace.push_back("QO");
    else if (p == incomingAddress)
      trace.push_back("QI");
  }
  realQueue(p);
}
extern "C" void realUnregister(TCardSPI *, ISysexReceiver *) asm(
    "__real__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_"
    "14ISysexReceiverE");
extern "C" void wrapUnregister(TCardSPI *, ISysexReceiver *) asm(
    "__wrap__ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_"
    "14ISysexReceiverE");
extern "C" void wrapUnregister(TCardSPI *p, ISysexReceiver *r) {
  if (capture)
    trace.push_back("U");
  realUnregister(p, r);
  assert(!SpiServiceAccess::state(*p).receivers.contains(r));
}
struct Offline final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { return 0; }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Clock final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { return 0; }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct OfflinePins final : presonus::surface_panel_port::InputPinIO {
  unsigned opened = 0, closed = 0;
  std::FILE *open(const char *, const char *) override {
    ++opened;
    return reinterpret_cast<std::FILE *>(std::uintptr_t(0x1000 + opened * 16));
  }
  int printPin(std::FILE *, const char *, int) override { return 1; }
  int close(std::FILE *) override {
    ++closed;
    return 0;
  }
  void formatPath(char *out, std::size_t n, const char *fmt, int pin) override {
    std::snprintf(out, n, fmt, pin);
  }
  std::size_t write(const void *, std::size_t, std::size_t n,
                    std::FILE *) override {
    return n;
  }
  int buffering(std::FILE *, char *, int, std::size_t) override { return 0; }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
  void log(const char *) override { std::abort(); }
};
struct Transport final : INetworkManager {
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
  int addExternalConnection(IConnection *&connection, IDataChannel *channel,
                            int port, unsigned char option,
                            IEventHandler *handler) override {
    std::abort();
  }
  int updateExternalConnection(IDataChannel *, int) override { std::abort(); }
  int removeExternalConnection(IDataChannel *channel) override { std::abort(); }
  int rescanAll(unsigned char) override { std::abort(); }
  int resetConnection() override { std::abort(); }
  int addErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int removeErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int simulateConnectionErrors() override { std::abort(); }
  int waitForOutgoingEvents(int) override { std::abort(); }
  int suspendNetworkAdapters(unsigned char) override { std::abort(); }
  int isSendingFromExternalConnection(int) override { std::abort(); }
};

struct Receiver final : ISysexReceiver {
  void receive(const SysexPacket &) override { std::abort(); }
  bool accepts(const SysexPacket &) override { std::abort(); }
};
static void fill(DicePacketQueue &q, int n) {
  for (int i = 0; i < n; ++i) {
    auto *p = new DataPacket<200>(PacketStorageTag{});
    packets[packetCount++] = p;
    p->length = i + 1;
    p->reusable = false;
    q.prependPacket(p);
  }
}
extern "C" void
nativeD1(TCardUCNetHandler *) asm("_ZN8Presonus4NOAA17TCardUCNetHandlerD1Ev");
extern "C" void
nativeD2(TCardUCNetHandler *) asm("_ZN8Presonus4NOAA17TCardUCNetHandlerD2Ev");
static void emit() {
  for (const auto &s : trace)
    std::cout << s << ' ';
  std::cout << std::endl;
  trace.clear();
}
int main(int argc, char **argv) {
  assert(argc == 8);
  std::string mode = argv[1], variant = argv[2];
  const bool endpoint = std::stoi(argv[3]), existing = std::stoi(argv[5]),
             registered = std::stoi(argv[6]), failure = std::stoi(argv[7]) != 0;
  const int failureMode = std::stoi(argv[7]);
  const int populated = std::stoi(argv[4]);
  static Offline offline;
  static OfflinePins pins;
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  setSpiServiceConstructionIO(&offline);
  assert(!SpiServiceAccess::singleton());
  if (existing || registered)
    TCardSPI::instance();
  Transport network;
  Clock clock;
  trace.reserve(64);
  if (mode == "provider") {
    Receiver receiver;
    auto *in = new DicePacketQueue;
    auto *out = new DicePacketQueue;
    auto *ep = endpoint ? new DiceEndPoint(*in, *out) : nullptr;
    fill(*in, populated);
    fill(*out, populated);
    incomingAddress = in;
    outgoingAddress = out;
    endpointAddress = ep;
    if (registered)
      TCardSPI::instance().registerReceiver(&receiver);
    capture = true;
    std::string op;
    while (std::cin >> op) {
      if (op == "L") {
        allocationCountdown = failure ? failureMode - 1 : -1;
        try {
          TCardSPI::instance();
          std::cout << "L" << std::endl;
        } catch (const std::bad_alloc &) {
          std::cout << "THROW";
          for (auto &s : trace)
            std::cout << ' ' << s;
          std::cout << std::endl;
          trace.clear();
        }
        allocationCountdown = -1;
      } else if (op == "U") {
        TCardSPI::instance().unRegisterReceiver(&receiver);
        emit();
      } else if (op == "E") {
        delete ep;
        ep = nullptr;
        emit();
      } else if (op == "O") {
        delete out;
        out = nullptr;
        emit();
      } else if (op == "I") {
        delete in;
        in = nullptr;
        emit();
      } else
        std::abort();
    }
    capture = false;
    if (failure)
      for (auto *pin : constructedPins)
        delete pin;
    delete ep;
    delete out;
    delete in;
    return 0;
  }
  if (mode == "borrowed") {
    DicePacketQueue in, out;
    fill(in, populated);
    fill(out, populated);
    UCNetHandlerState state{in, network, clock, nullptr, nullptr,
                            0,  0,       0,     &out,    0};
    auto *h = new TCardUCNetHandler(ucNetHandlerSetupTag, state);
    if (registered)
      TCardSPI::instance().registerReceiver(h);
    incomingAddress = &in;
    outgoingAddress = &out;
    selfAddress = h;
    capture = true;
    delete h;
    capture = false;
    assert(in.getTotalBytes() == unsigned(populated * (populated + 1) / 2));
    assert(out.getTotalBytes() == in.getTotalBytes());
    assert(bool(SpiServiceAccess::singleton()) == bool(existing || registered));
    emit();
    return 0;
  }
  if (mode == "adapter") {
    TCardUCNetHandler h(ucNetHandlerOwnedSetupTag, network, clock, true);
    auto &v = h.portableState();
    auto *channel = v.channel;
    assert(channel && !channel->isReadable(1) && channel->isWritable(1));
    const char bytes[]{1, 2, 3};
    char readback[3]{};
    assert(v.incoming.write(bytes, 3) == 3);
    assert(channel->getBytesAvailable() == 3 && channel->isReadable(1));
    assert(channel->read(readback, 3) == 3 &&
           std::equal(readback, readback + 3, bytes));
    assert(channel->write(bytes, 3) == 3 && v.outgoing->getTotalBytes() == 3);
    assert(channel->getGranularity() == 200 && !channel->hasErrors(0));
    std::cout << "ADAPTER" << std::endl;
    return 0;
  }
  auto *h = new TCardUCNetHandler(ucNetHandlerOwnedSetupTag, network, clock,
                                  endpoint);
  auto &state = h->portableState();
  fill(state.incoming, populated);
  fill(*state.outgoing, populated);
  incomingAddress = &state.incoming;
  outgoingAddress = state.outgoing;
  endpointAddress = h->portableOwnedEndpoint();
  selfAddress = h;
  if (registered)
    TCardSPI::instance().registerReceiver(h);
  capture = true;
  allocationCountdown = failure ? failureMode - 1 : -1;
  bool caught = false;
  try {
    if (variant == "D0")
      delete h;
    else if (variant == "D1")
      nativeD1(h);
    else {
      assert(variant == "D2");
      nativeD2(h);
    }
  } catch (const std::bad_alloc &) {
    caught = true;
  }
  allocationCountdown = -1;
  capture = false;
  assert(caught == failure);
  auto *retainedEndpoint = static_cast<DiceEndPoint *>(endpointAddress);
  assert(failure ? bool(retainedEndpoint) == endpoint : !endpointAddress);
  if (variant != "D0") {
    assert(selfAddress == h);
    __real__ZdlPv(h);
    selfAddress = nullptr;
  } else
    assert(!selfAddress);
  if (failure) {
    assert(!SpiServiceAccess::singleton());
    assert(pins.opened - pins.closed == unsigned(failureMode == 3));
    trace.insert(trace.begin(), "THROW");
  }
  emit();
  // The actual native failure path retains endpoint. Clean it only after the
  // observed function trace, with capture disabled; no invented function event.
  delete retainedEndpoint;
  endpointAddress = nullptr;
  if (failure) {
    for (auto *pin : constructedPins)
      delete pin;
    assert(pins.opened == pins.closed);
  }
}
