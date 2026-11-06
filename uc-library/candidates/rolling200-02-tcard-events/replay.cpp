#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/status_property.hpp"
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static unsigned clocks, statusCalls, macCalls, ackCalls, generated, serial;
static unsigned char ack;
static std::vector<SysexPacket> packets;
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  return -1000001 + std::int64_t(clocks++) * 1000003;
}
} // namespace presonus::dice
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
  std::int32_t updateFirmware(Presonus::UC::IFirmwareUpdateListener *,
                              int) override {
    std::abort();
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &s, Response &r)
      : TCardHandler(cardHandlerSetupTag, s, r) {}
  void setProperty(const Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
  int threadEntry() override { std::abort(); }
  void post(SysexPacket &p) override { packets.push_back(p); }
};

#include <atomic>
#include <thread>
#include <unistd.h>
static std::atomic<std::uint32_t> pending;
static std::vector<unsigned> schedule, observed;
static bool bounded, realSleep;
struct Bound {};
extern "C" int __real_usleep(useconds_t);
extern "C" int __wrap_usleep(useconds_t us) {
  if (realSleep)
    return __real_usleep(us);
  assert(us == 10000);
  observed.push_back(us / 1000);
  auto n = observed.size();
  if (bounded && n == 8)
    throw Bound{};
  pending.store(schedule[std::min(n, schedule.size() - 1)],
                std::memory_order_release);
  return 0;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  Response response;
  IO io;
  CardState cs{};
  Card card(cs, response, io);
  CardHandlerState state{card};
  Handler handler(state, response);
  bool rejected = false;
  try {
    handler.purgeEvents();
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  assert(rejected);
  state.pendingEventCount = &pending;
  std::ifstream f(argv[1]);
  assert(f);
  unsigned n, count = 0;
  while (f >> n) {
    schedule.resize(n);
    for (auto &x : schedule)
      f >> x;
    unsigned sleeps, returned;
    f >> sleeps >> returned;
    observed.clear();
    pending.store(schedule[0], std::memory_order_release);
    bounded = !returned;
    bool stopped = false;
    try {
      handler.purgeEvents();
    } catch (const Bound &) {
      stopped = true;
    }
    assert(stopped == bounded);
    assert(observed.size() == sleeps);
    for (auto x : observed)
      assert(x == 10);
    assert(pending.load() == (returned ? 0 : schedule[0]));
    ++count;
  }
  // Actual pinned provider path and real POSIX sleep, with independent
  // producer.
  realSleep = true;
  pending.store(1, std::memory_order_release);
  std::thread producer([] {
    __real_usleep(15000);
    pending.store(0, std::memory_order_release);
  });
  handler.purgeEvents();
  producer.join();
  assert(pending.load() == 0);
  std::cout << "5 native schedules matched; null binding rejected; actual "
               "CCL/POSIX sleep smoke passed\n";
  assert(count == 5);
}
