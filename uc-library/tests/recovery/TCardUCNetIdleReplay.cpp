#include "presonus/noaa/ucnet_handler.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <time.h>
#include <vector>
using namespace Presonus::UC;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::vector<long long> ticks;
static unsigned clockIndex;
static bool clocksActive;
static std::vector<std::string> posts;
static std::vector<unsigned> clockAtPost;
static std::vector<std::array<std::uint64_t, 3>> poststates;
static UCNetHandlerState *activeState;
extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *out) {
  if (!clocksActive)
    return __real_clock_gettime(id, out);
  assert(id == CLOCK_MONOTONIC && clockIndex < ticks.size());
  const auto t = ticks[clockIndex++];
  out->tv_sec = t / 1000;
  out->tv_nsec = (t % 1000) * 1000000;
  return 0;
}
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool) override { std::abort(); }
};
struct Offline final : SpiServiceIO {
  unsigned transfers = 0;
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { return 0; }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
  int transfer(int descriptor, const SpiTransfer &t) override {
    assert(descriptor == -1 && t.length > 0);
    static const char hex[] = "0123456789abcdef";
    std::string s;
    for (unsigned i = 0; i < t.length; ++i) {
      s += hex[t.tx[i] >> 4];
      s += hex[t.tx[i] & 15];
      t.rx[i] = 0xf8;
    }
    posts.push_back(s);
    clockAtPost.push_back(clockIndex);
    poststates.push_back({activeState->observedWord60,
                          activeState->observedTicks68,
                          activeState->observedByte8});
    ++transfers;
    return t.length;
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
static OfflinePins *pinCapture;
static void verifyTeardown() {
  assert(!SpiServiceAccess::singleton());
  assert(pinCapture->opened == 6 && pinCapture->closed == 6);
  std::cout << "{\"actual_ccl_registered_teardown\":true,\"gpio_operations_"
               "captured\":true}\n";
}
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

int main() {
  // Static lifetime outlasts the pinned CCL Deletable registry's teardown.
  static Offline offline;
  static OfflinePins pins;
  pinCapture = &pins;
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  std::atexit(verifyTeardown);
  setSpiServiceConstructionIO(&offline);
  assert(!SpiServiceAccess::singleton());
  Transport network;
  Pump pump;
  presonus::dice::CclResponseServices clock(pump);
  unsigned cases = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    unsigned flag, n, expectedFlag, expectedByte, remaining, expectedClocks,
        count;
    std::uint64_t last, expectedLast;
    long long received;
    in >> flag >> n >> last >> received >> expectedFlag >> expectedLast >>
        expectedByte >> remaining >> expectedClocks >> count;
    ticks.resize(25); // handshake script length; idle scripts contain three.
    ticks.resize(flag ? 25 : 3);
    for (auto &t : ticks)
      in >> t;
    std::vector<std::string> expected(count);
    for (auto &s : expected)
      in >> s;
    std::vector<std::array<std::uint64_t, 3>> expectedStates(count);
    for (auto &row : expectedStates)
      for (auto &v : row)
        in >> v;
    assert(in);
    DicePacketQueue incoming, outgoing;
    const std::array<unsigned char, 255> midi = [] {
      std::array<unsigned char, 255> b{};
      b[0] = 0xf0;
      b[1] = 0x40;
      b[8] = 0xf7;
      return b;
    }();
    assert(incoming.writeMIDI(midi.data()));
    for (unsigned i = 0; i < n; ++i) {
      auto b = midi;
      b[7] = i & 15;
      assert(outgoing.writeMIDI(b.data()));
    }
    UCNetHandlerState state{incoming, network, clock,    nullptr,   nullptr,
                            1,        flag,    received, &outgoing, last};
    activeState = &state;
    TCardUCNetHandler handler(ucNetHandlerSetupTag, state);
    posts.clear();
    poststates.clear();
    clockAtPost.clear();
    clockIndex = 0;
    clocksActive = true;
    handler.idleIO();
    clocksActive = false;
    assert(state.observedWord60 == expectedFlag &&
           state.observedByte8 == expectedByte &&
           state.observedTicks68 == expectedLast &&
           state.observedTicks70 == received);
    assert(clockIndex == expectedClocks && posts == expected &&
           poststates == expectedStates);
    // Native clock reads precede each drain post; control packet has two reads.
    if (flag) {
      for (unsigned i = 0; i + 1 < count; ++i)
        assert(clockAtPost[i] == i + 1);
      assert(clockAtPost.back() == count + 1);
    } else if (count)
      assert(clockAtPost[0] == 3);
    assert(incoming.getTotalBytes() == 4);
    unsigned actualRemaining = 0;
    while (!outgoing.isEmpty()) {
      unsigned char len = 0;
      std::array<unsigned char, 255> b{};
      outgoing.readMIDI(b.data(), len);
      ++actualRemaining;
    }
    assert(actualRemaining == remaining);
    ++cases;
  }
  assert(SpiServiceAccess::singleton() &&
         SpiServiceAccess::pinCount(TCardSPI::instance()) == 2);
  assert(cases == 33);
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"actual_ccl_clock_and_singleton\":true,\"physical_"
               "operations\":0}\n";
  // Actual pinned Deletable list destroys lazy owned singleton at process exit.
}
