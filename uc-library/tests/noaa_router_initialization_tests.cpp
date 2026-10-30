#include "presonus/noaa/diagnostics.hpp"
#include "presonus/noaa/router.hpp"
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using namespace presonus::noaa;
using namespace presonus::dice;
using namespace Presonus::NOAA;
struct Context;
static Context *active;
static thread_local bool observe = true;
struct Context {
  RouterState *state = nullptr;
  TCardRouter *router = nullptr;
  std::vector<std::string> events;
  std::vector<SysexPacket> packets;
  std::int64_t tickBase = 0;
  unsigned clocks = 0, ack = 1, status = 1, depth = 0;
  bool overrideCount = false, throwPost = false, throwLog = false,
       probe = false, reenter = false;
  std::uint32_t count = 0;
  unsigned probes = 0, reentries = 0;
};
static void store(RouterState &state, std::uint32_t word) {
  for (unsigned i = 0; i < 4; ++i)
    state.applicationBytes[260 + i] =
        static_cast<unsigned char>(word >> (8 * i));
}
static std::uint32_t load(const RouterState &state) {
  std::uint32_t result = 0;
  for (unsigned i = 0; i < 4; ++i)
    result |= std::uint32_t(state.applicationBytes[260 + i]) << (8 * i);
  return result;
}
extern "C" void __real__ZN4Core8Platform9PosixLock4lockEv(void *);
extern "C" void __real__ZN4Core8Platform9PosixLock6unlockEv(void *);
extern "C" void __wrap__ZN4Core8Platform9PosixLock4lockEv(void *p) {
  __real__ZN4Core8Platform9PosixLock4lockEv(p);
  if (active && observe) {
    ++active->depth;
    active->events.emplace_back("lock");
    if (active->overrideCount) {
      store(*active->state, active->count);
      active->overrideCount = false;
    }
  }
}
extern "C" void __wrap__ZN4Core8Platform9PosixLock6unlockEv(void *p) {
  if (active && observe) {
    assert(active->depth > 0);
    --active->depth;
    active->events.emplace_back("unlock");
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(p);
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  assert(active);
  return active->tickBase + std::int64_t(active->clocks++) * 1000003;
}
} // namespace presonus::dice
static void probeLock() {
  std::atomic<bool> acquired{false};
  auto &lock = active->state->lock;
  std::thread other([&] {
    observe = false;
    acquired = lock.tryLock();
    if (acquired)
      lock.unlock();
  });
  other.join();
  assert(acquired == (active->depth == 0));
  ++active->probes;
}
static std::string hexBytes(const unsigned char *p, std::size_t size) {
  static const char digits[] = "0123456789abcdef";
  std::string out;
  for (std::size_t i = 0; i < size; ++i) {
    out += digits[p[i] >> 4];
    out += digits[p[i] & 15];
  }
  return out;
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  assert(active);
  va_list args;
  va_start(args, fmt);
  if (std::strcmp(fmt, "!!!!!!!!!!!!!!! missed Route\n") == 0)
    active->events.emplace_back("capacity_error");
  else {
    assert(std::strcmp(fmt, "NOAA: %s\n") == 0);
    const auto *text = va_arg(args, const char *);
    active->events.emplace_back(
        "noaahex:" + hexBytes(reinterpret_cast<const unsigned char *>(text),
                              std::strlen(text)));
  }
  va_end(args);
}
struct Response final : ResponseServices {
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
  void diagnostic(bool out, const char *fmt, int value, bool arg) override {
    assert(!out && std::strcmp(fmt, "route err found") == 0 && value == 0 &&
           !arg);
    active->events.emplace_back("bulk_error");
  }
};
struct Fixture final : TCardRouter {
  Fixture(RouterState &s, Response &r, IO &io)
      : TCardRouter(s, r, io, rm13731LinkAddressRouterLookup()) {}
  void post(SysexPacket &packet) override {
    assert(active);
    active->packets.push_back(packet);
    if (observe)
      active->events.emplace_back("post:" + std::to_string(packet.length) +
                                  ":" + std::to_string(active->depth));
    portableState().command = 0;
    portableState().status = 0;
    if (active->probe)
      probeLock();
    if (active->reenter && active->reentries == 0) {
      ++active->reentries;
      assert(addIdleRoute(1, 2, 3, 4));
    }
    if (active->throwPost)
      throw std::runtime_error("post boundary failure");
  }
};
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *receiver,
                                                  long long timeout) {
  assert(active && receiver == active->router && timeout == 500);
  receiver->portableState().command = static_cast<unsigned char>(active->ack);
  receiver->portableState().status = static_cast<unsigned char>(active->status);
  if (observe)
    active->events.emplace_back("wait500");
  return static_cast<unsigned char>(active->ack);
}

static std::vector<unsigned char> unhex(const std::string &s) {
  std::vector<unsigned char> b;
  for (size_t i = 0; i < s.size(); i += 2)
    b.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return b;
}

extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter15doRouteCommandsEPNS0_9DiceRouteEih(
    TCardRouter *, DiceRoute *, int, unsigned char);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter15doRouteCommandsEPNS0_9DiceRouteEih(
    TCardRouter *router, DiceRoute *routes, int count, unsigned char remap) {
  assert(active && router == active->router && count >= 0 && count <= 60 &&
         remap == 1);
  active->events.emplace_back(
      "bulk:" + std::to_string(count) + ":" + std::to_string(remap) + ":" +
      hexBytes(reinterpret_cast<unsigned char *>(routes), 4 * count));
  const auto old = observe;
  observe = false;
  try {
    __real__ZN8Presonus4NOAA11TCardRouter15doRouteCommandsEPNS0_9DiceRouteEih(
        router, routes, count, remap);
  } catch (...) {
    observe = old;
    throw;
  }
  observe = old;
}
int main(int argc, char **argv) {
  assert(argc == 3);
  std::ifstream input(argv[1]);
  assert(input);
  std::string line;
  unsigned cases = 0, bulkCalls = 0;
  while (std::getline(input, line)) {
    std::istringstream in(line);
    std::string name, tableHex, expectedHex;
    int32_t count;
    unsigned seed, argument;
    in >> name >> count >> seed >> tableHex >> argument >> expectedHex;
    assert(in);
    RouterState state;
    for (unsigned i = 0; i < state.applicationBytes.size(); ++i)
      state.applicationBytes[i] =
          static_cast<unsigned char>(seed + (i + 24) * 29);
    state.applicationBytes[256] = 0;
    store(state, static_cast<uint32_t>(count));
    const auto expected = unhex(expectedHex);
    assert(expected.size() == state.applicationBytes.size());
    unsigned eventCount;
    in >> eventCount;
    std::vector<std::string> events(eventCount);
    for (auto &event : events)
      in >> event;
    unsigned packetCount;
    in >> packetCount;
    std::vector<std::vector<unsigned char>> packets(packetCount);
    for (auto &packet : packets) {
      std::string hex;
      in >> hex;
      packet = unhex(hex);
    }
    assert(in);
    assert(tableHex.size() == 160);
    auto adc = unhex(tableHex.substr(0, 80)),
         dac = unhex(tableHex.substr(80, 48)),
         geq = unhex(tableHex.substr(128, 32));
    unsigned char adcArray[40], dacArray[24], eqArray[16];
    std::copy(adc.begin(), adc.end(), adcArray);
    std::copy(dac.begin(), dac.end(), dacArray);
    std::copy(geq.begin(), geq.end(), eqArray);
    RouterSlotTables tables(adcArray, dacArray, eqArray);
    state.slotTables = &tables;
    Context context;
    context.state = &state;
    Response response;
    IO io;
    Fixture router(state, response, io);
    context.router = &router;
    active = &context;
    if (name == "initRoutes")
      router.initRoutes();
    else {
      assert(name == "routeAnalogIns" && argument <= 1);
      router.routeAnalogIns(argument != 0);
    }
    assert(std::equal(expected.begin(), expected.end(),
                      state.applicationBytes.begin()));
    assert(context.events == events);
    assert(context.packets.size() == packets.size());
    for (unsigned i = 0; i < packets.size(); ++i) {
      assert(context.packets[i].length == packets[i].size());
      assert(std::equal(packets[i].begin(), packets[i].end(),
                        context.packets[i].bytes.begin()));
      ++bulkCalls;
    }
    assert(context.depth == 0);
    active = nullptr;
    ++cases;
  }
  std::ifstream printInput(argv[2]);
  assert(printInput);
  std::string inputHex, expectedHex;
  unsigned expectedCalls, printCases = 0;
  while (printInput >> inputHex >> expectedCalls >> expectedHex) {
    auto text =
        inputHex == "-" ? std::vector<unsigned char>{} : unhex(inputHex);
    text.push_back(0);
    Context context;
    active = &context;
    printNOAA(reinterpret_cast<const char *>(text.data()));
    std::vector<std::string> expected;
    if (expectedCalls) {
      assert(expectedCalls == 1);
      expected.push_back("noaahex:" + expectedHex);
    }
    assert(context.events == expected);
    active = nullptr;
    ++printCases;
  }
  assert(printInput.eof() && printCases == 24);
  std::cout << "{\"passed\":true,\"initialization_cases\":" << cases
            << ",\"print_cases\":" << printCases
            << ",\"real_bulk_calls\":" << bulkCalls
            << ",\"actual_device_operations\":0}\n";
}
