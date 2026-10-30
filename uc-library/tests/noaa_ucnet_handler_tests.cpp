
#include "presonus/noaa/ucnet_handler.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <time.h>
#include <vector>
using namespace Presonus::UC;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static UCNetHandlerState *activeState;
static IConnection *oldConnection, *newConnection;
static int expectedPort, callbackResult;
static unsigned networkCalls, clockCalls;
static std::int64_t rawTicks;
static std::uint32_t oldWord;
static std::int64_t oldTime;
static bool actualClockSmoke;
extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *out) {
  if (!actualClockSmoke)
    return __real_clock_gettime(id, out);
  assert(id == CLOCK_MONOTONIC && activeState &&
         activeState->observedByte8 == 1 &&
         activeState->observedWord60 == oldWord &&
         activeState->observedTicks70 == oldTime);
  ++clockCalls;
  out->tv_sec = 2;
  out->tv_nsec = 345678901;
  return 0;
}
struct Clock final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override {
    assert(activeState && activeState->observedByte8 == 1 &&
           activeState->observedWord60 == oldWord &&
           activeState->observedTicks70 == oldTime);
    ++clockCalls;
    return rawTicks;
  }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool) override { std::abort(); }
};
static std::vector<unsigned char> unhex(const std::string &s) {
  std::vector<unsigned char> b;
  for (size_t i = 0; i < s.size(); i += 2)
    b.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return b;
}
extern "C" __attribute__((noinline)) bool
ucnet_virtual_accepts(ISysexReceiver *p, const SysexPacket &v) {
  return p->accepts(v);
}
extern "C" __attribute__((noinline)) void
ucnet_virtual_receive(ISysexReceiver *p, const SysexPacket &v) {
  p->receive(v);
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
    assert(activeState && &connection == &activeState->connection &&
           channel == activeState->channel && port == expectedPort &&
           option == 0 && !handler);
    assert(connection == oldConnection);
    ++networkCalls;
    connection = newConnection;
    return callbackResult;
  }
  int updateExternalConnection(IDataChannel *, int) override { std::abort(); }
  int removeExternalConnection(IDataChannel *channel) override {
    assert(activeState && channel == activeState->channel &&
           activeState->connection == oldConnection);
    ++networkCalls;
    return callbackResult;
  }
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
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string line;
  unsigned cases = 0;
  Transport network;
  Clock clock;
  DicePacketQueue queue;
  std::array<unsigned, 4> tokens{};
  auto connection = [&](unsigned x) {
    return x ? reinterpret_cast<IConnection *>(&tokens[x == 0x20009200 ? 3 : 2])
             : nullptr;
  };
  UCNetHandlerState state{queue, network, clock, nullptr, nullptr, 0, 0, 0};
  TCardUCNetHandler handler(ucNetHandlerSetupTag, state);
  activeState = &state;
  while (std::getline(file, line)) {
    std::istringstream in(line);
    std::string method, payloadHex, queueHex;
    unsigned length, flag, word, conn, ch, newConn, ret, expectedFlag,
        expectedWord, expectedConn, expectedClocks, queueSuccess, queueLength;
    long long ticks, time, expectedTime;
    int port, result;
    in >> method >> length >> payloadHex >> ticks >> flag >> word >> time >>
        conn >> ch >> port >> newConn >> result >> ret >> expectedFlag >>
        expectedWord >> expectedTime >> expectedConn >> expectedClocks >>
        queueSuccess >> queueLength >> queueHex;
    state.observedByte8 = flag;
    state.observedWord60 = word;
    state.observedTicks70 = time;
    state.connection = connection(conn);
    state.channel = ch ? reinterpret_cast<IDataChannel *>(&tokens[1]) : nullptr;
    oldConnection = state.connection;
    newConnection = connection(newConn);
    expectedPort = port;
    callbackResult = result;
    clockCalls = networkCalls = 0;
    rawTicks = ticks;
    oldWord = word;
    oldTime = time;
    SysexPacket packet;
    packet.length = length;
    auto payload = unhex(payloadHex);
    assert(payload.size() == 256);
    std::copy(payload.begin(), payload.end(), packet.bytes.begin());
    if (method == "accepts")
      assert(ucnet_virtual_accepts(&handler, packet) == bool(ret));
    else if (method == "receive")
      ucnet_virtual_receive(&handler, packet);
    else if (method == "startup")
      assert(static_cast<std::uint32_t>(handler.startup(port)) == ret);
    else {
      assert(method == "shutdown");
      assert(static_cast<std::uint32_t>(handler.shutdown()) == ret);
    }
    assert(state.observedByte8 == expectedFlag &&
           state.observedWord60 == expectedWord &&
           state.observedTicks70 == expectedTime &&
           state.connection == connection(expectedConn));
    assert(clockCalls == expectedClocks);
    assert(networkCalls ==
           unsigned(method == "startup" || method == "shutdown"));
    if (method == "receive") {
      std::array<unsigned char, 255> out;
      out.fill(0x39);
      unsigned char n = 0x9a;
      bool ok = queue.readMIDI(out.data(), n);
      auto expected = unhex(queueHex);
      assert(ok == bool(queueSuccess) && n == queueLength &&
             expected.size() == 255 &&
             std::equal(out.begin(), out.end(), expected.begin()));
      queue.flush();
    }
    ++cases;
  }
  Pump pump;
  presonus::dice::CclResponseServices cclClock(pump);
  UCNetHandlerState real{queue,   network, cclClock,   nullptr,
                         nullptr, 0,       0x12345678, -5};
  TCardUCNetHandler realHandler(ucNetHandlerSetupTag, real);
  activeState = &real;
  oldWord = real.observedWord60;
  oldTime = real.observedTicks70;
  clockCalls = 0;
  actualClockSmoke = true;
  SysexPacket packet;
  packet.length = 2;
  packet.bytes[1] = 64;
  realHandler.receive(packet);
  actualClockSmoke = false;
  assert(clockCalls == 1 && real.observedWord60 == 1 &&
         real.observedTicks70 == 2345);
  activeState = nullptr;
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"actual_ccl_clock_smoke\":true,\"actual_queue_graph\":true,"
               "\"physical_operations\":0}\n";
}
