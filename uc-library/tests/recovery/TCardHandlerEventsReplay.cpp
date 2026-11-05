#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/card_handler_events.hpp"
#include "presonus/noaa/router.hpp"
#include "presonus/noaa/spi_packets.hpp"
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <time.h>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
namespace {
std::vector<std::int64_t> times;
std::vector<unsigned> expectedIdle, actualIdle, expectedSpi, actualSpi;
std::vector<Core::PropertyType> dispatched, expectedTypes;
std::vector<unsigned> expectedPending, expectedNodes;
CardHandlerEventQueue *runningQueue;
std::map<void *, unsigned> locks;
std::vector<void *> lockOrder;
std::vector<std::vector<unsigned char>> packets;
CardHandlerState *running;
unsigned iteration;
bool captureLocks, observeDispatch, throwDispatch;
} // namespace
namespace presonus::dice {
std::int64_t packetClockRawTicks() { return 1000000; }
} // namespace presonus::dice
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  assert(running && clock == CLOCK_MONOTONIC && iteration < times.size());
  const auto ms = times[iteration];
  value->tv_sec = ms / 1000;
  value->tv_nsec = (ms % 1000) * 1000000;
  return 0;
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned ms) {
  assert(ms == 2 && running);
  assert(runningQueue->pending() == expectedPending[iteration]);
  assert(runningQueue->queuedNodes() == expectedNodes[iteration]);
  if (++iteration == times.size())
    running->stopRequested.store(true, std::memory_order_release);
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  if (captureLocks) {
    ++locks[p];
    lockOrder.push_back(p);
  }
}
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (captureLocks) {
    assert(locks[p] > 0);
    --locks[p];
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
extern "C" void
__real__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
    TCardHandler *, const Core::Property &);
extern "C" void
__wrap__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
    TCardHandler *h, const Core::Property &p) {
  assert(observeDispatch && lockOrder.size() >= 2 &&
         lockOrder[0] != lockOrder[1]);
  assert(locks[lockOrder[0]] == 1 && locks[lockOrder[1]] == 1);
  dispatched.push_back(p.type);
  if (throwDispatch)
    throw std::runtime_error("captured dispatch exception");
  __real__ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE(
      h, p);
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter4idleEv(TCardRouter *);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter4idleEv(TCardRouter *p) {
  actualIdle.push_back(iteration);
  __real__ZN8Presonus4NOAA11TCardRouter4idleEv(p);
}
extern "C" void __real__ZN8Presonus4NOAA8TCardSPI6onIdleEb(TCardSPI *, bool);
extern "C" void __wrap__ZN8Presonus4NOAA8TCardSPI6onIdleEb(TCardSPI *p,
                                                           bool read) {
  actualSpi.push_back(read);
  __real__ZN8Presonus4NOAA8TCardSPI6onIdleEb(p, read);
}
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *p,
                                                  long long t) {
  assert(t == 500);
  p->portableState().status = 1;
  return 1;
}
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct Card final : TCard {
  Card(CardState &s, Response &r, IO &i) : TCard(cardSetupTag, s, r, i) {}
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &p) override {
    packets.emplace_back(p.bytes.begin(), p.bytes.begin() + p.length);
  }
};
struct Router final : TCardRouter {
  Router(RouterState &s, Response &r, IO &i)
      : TCardRouter(s, r, i, rm13731LinkAddressRouterLookup()) {}
  void post(SysexPacket &p) override {
    packets.emplace_back(p.bytes.begin(), p.bytes.begin() + p.length);
    portableState().command = 0;
    portableState().status = 0;
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &s, Response &r)
      : TCardHandler(cardHandlerSetupTag, s, r) {}
  void setProperty(const Core::Property &) override { std::abort(); }
  void post(SysexPacket &p) override {
    packets.emplace_back(p.bytes.begin(), p.bytes.begin() + p.length);
  }
};
static void clearCapture() {
  locks.clear();
  lockOrder.clear();
  dispatched.clear();
}
int main(int argc, char **argv) {
  assert(argc == 3);
  std::ifstream f(argv[1]);
  assert(f);
  std::string line, selected = argv[2];
  bool found = false;
  while (std::getline(f, line)) {
    std::istringstream in(line);
    std::string name;
    unsigned n;
    in >> name >> n;
    if (name != selected)
      continue;
    found = true;
    times.resize(n);
    for (auto &t : times)
      in >> t;
    in >> n;
    expectedIdle.resize(n);
    for (auto &v : expectedIdle)
      in >> v;
    in >> n;
    expectedSpi.resize(n);
    for (auto &v : expectedSpi)
      in >> v;
    in >> n;
    expectedTypes.resize(n);
    for (auto &v : expectedTypes)
      in >> v;
    expectedPending.resize(times.size());
    expectedNodes.resize(times.size());
    for (auto &v : expectedPending)
      in >> v;
    for (auto &v : expectedNodes)
      in >> v;
  }
  assert(found);
  Response response;
  IO io;
  auto *priorIO = setSpiServiceConstructionIO(&io);
  CardState cs{};
  cs.observedWord3c = 23;
  Card card(cs, response, io);
  RouterState rs{};
  rs.applicationBytes.fill(0);
  rs.slotTables = &rm13731GambitRouterSlots();
  Router router(rs, response, io);
  SpiPacketState spiState({}, 0, 1, 8);
  TCardSPI spi(spiState);
  auto *priorSPI = SpiServiceAccess::singleton();
  SpiServiceAccess::singleton(&spi);
  CardHandlerState hs{card};
  hs.router = &router;
  Handler handler(hs, response);
  CardHandlerEventQueue queue(1, 2, 2);
  queue.bind(hs);
  runningQueue = &queue;
  if (selected == "fifo-pools") {
    for (auto bytes : {16, 17, 32, 33, 512}) {
      Core::Property p(100 + queue.pending(), bytes);
      assert(queue.enqueue(CardHandlerEvent(p, bytes)));
    }
    queue.enqueueNull();
    assert(queue.pending() == 5 && queue.queuedNodes() == 6);
  }
  hs.stopRequested.store(selected == "stopped");
  running = &hs;
  captureLocks = observeDispatch = true;
  assert(handler.threadEntry() == 0);
  captureLocks = observeDispatch = false;
  assert(actualIdle == expectedIdle && actualSpi == expectedSpi &&
         iteration == times.size());
  assert(queue.pending() == 0 && queue.queuedNodes() == 0);
  for (auto [p, depth] : locks)
    assert(depth == 0);
  assert(dispatched == expectedTypes);
  // Same process/another instance: shared static deadline must persist. Clock0
  // never exceeds any positive deadline produced by the selected fixture.
  if (selected == "deadlines") {
    CardHandlerState other{card};
    other.router = &router;
    Handler second(other, response);
    actualIdle.clear();
    times = {0};
    expectedPending = {0};
    expectedNodes = {0};
    iteration = 0;
    running = &other;
    assert(second.threadEntry() == 0);
    assert(actualIdle.empty());
  }
  // Typed queue integration is additional source-port coverage, independent of
  // native thread control traces. Execute real deferred bodies on copied data.
  if (selected == "fifo-pools") {
    running = &hs;
    captureLocks = observeDispatch = true;
    Core::Property original(1399157877, 40);
    DeferredRateProjection priorRate{&original, 1, 2};
    DeferredRouteProjection priorRoute{&original, 0, 0, 0, 0, 0};
    std::array<unsigned char, 33> priorPayload{};
    hs.deferredRate = &priorRate;
    hs.deferredRoutes = &priorRoute;
    hs.geqProperty = &original;
    hs.geqPayload = &priorPayload;
    CardHandlerEvent rate(original, 40);
    rate.rate = DeferredRateProjection{&original, 48000.f, 7};
    assert(queue.enqueue(rate));
    rate.rate->value08 = 96000;
    rate.rate->link1c = 99;
    original.type = 0;
    packets.clear();
    clearCapture();
    queue.consumeOne(handler, hs);
    assert(packets.size() == 2 && packets[1][2] == 1 && packets[1][3] == 7);
    assert(hs.deferredRate == &priorRate && hs.deferredRoutes == &priorRoute &&
           hs.geqProperty == &original && hs.geqPayload == &priorPayload);
    Core::Property gp(1936225136, 41);
    CardHandlerEvent geq(gp, 41);
    geq.geq.emplace();
    for (unsigned i = 0; i < 33; ++i)
      (*geq.geq)[i] = i + 128;
    assert(queue.enqueue(geq));
    geq.geq->fill(255);
    packets.clear();
    clearCapture();
    queue.consumeOne(handler, hs);
    assert(packets.size() == 1 && packets[0].size() == 36);
    for (unsigned i = 0; i < 33; ++i)
      assert(packets[0][i + 2] == i);
    Core::Property rp(1634038640, 40);
    CardHandlerEvent route(rp, 40);
    route.routes = DeferredRouteProjection{&rp, 0, 0, 0, 0, 0};
    assert(queue.enqueue(route));
    route.routes->count10 = 1;
    packets.clear();
    clearCapture();
    queue.consumeOne(handler, hs);
    const auto routePackets = packets;
    const auto routeState = rs.applicationBytes;
    rs.applicationBytes.fill(0);
    packets.clear();
    router.initRoutes();
    assert(packets == routePackets && rs.applicationBytes == routeState);
    Core::Property unknown(0, 8);
    CardHandlerEvent small(unknown, 16);
    assert(queue.enqueue(small));
    assert(!queue.enqueue(small));
    throwDispatch = true;
    clearCapture();
    bool caught = false;
    try {
      queue.consumeOne(handler, hs);
    } catch (const std::runtime_error &) {
      caught = true;
    }
    throwDispatch = false;
    assert(caught && queue.pending() == 0);
    assert(hs.deferredRate == &priorRate && hs.deferredRoutes == &priorRoute &&
           hs.geqProperty == &original && hs.geqPayload == &priorPayload);
    for (auto [p, depth] : locks)
      assert(depth == 0);
    assert(queue.enqueue(small));
    clearCapture();
    queue.consumeOne(handler, hs);
    for (int bytes : {0, 513}) {
      bool invalid = false;
      try {
        queue.enqueue(CardHandlerEvent(unknown, bytes));
      } catch (const std::invalid_argument &) {
        invalid = true;
      }
      assert(invalid);
    }
    captureLocks = observeDispatch = false;
  }
  queue.unbind(hs);
  running = nullptr;
  SpiServiceAccess::singleton(priorSPI);
  setSpiServiceConstructionIO(priorIO);
  std::cout << "PASS " << selected
            << " native control trace, actual deferred/router/SPI bodies, CCL "
               "locks/pools; no device I/O\n";
}
