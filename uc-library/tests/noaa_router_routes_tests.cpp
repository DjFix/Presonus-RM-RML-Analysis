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
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  assert(active);
  va_list args;
  va_start(args, fmt);
  if (std::strcmp(fmt, "!!!!!!!!!!!!!!! missed Route\n") == 0)
    active->events.emplace_back("capacity_error");
  else {
    assert(std::strcmp(fmt,
                       "ESA: Add ADC route, dantechannel: %d, adcslot: %d\n") ==
           0);
    int d = va_arg(args, int), s = va_arg(args, int);
    active->events.push_back("dante:" + std::to_string(d) + ":" +
                             std::to_string(s));
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
    active->events.emplace_back("post:" + std::to_string(packet.length) + ":" +
                                std::to_string(active->depth));
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
  active->events.emplace_back("wait500");
  return static_cast<unsigned char>(active->ack);
}

static std::vector<unsigned char> unhex(const std::string &s) {
  std::vector<unsigned char> b;
  for (size_t i = 0; i < s.size(); i += 2)
    b.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return b;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string line;
  unsigned cases = 0;
  while (std::getline(file, line)) {
    std::istringstream in(line);
    std::string name, tableHex, diffHex;
    int32_t count;
    unsigned seed, nargs;
    in >> name >> count >> seed >> tableHex >> nargs;
    std::vector<int> args(nargs);
    for (auto &n : args)
      in >> n;
    RouterState state;
    for (unsigned i = 0; i < state.applicationBytes.size(); ++i)
      state.applicationBytes[i] =
          static_cast<unsigned char>(seed + (i + 24) * 29);
    state.applicationBytes[256] = 0;
    store(state, static_cast<uint32_t>(count));
    auto expected = state.applicationBytes;
    unsigned changes;
    in >> changes;
    for (unsigned i = 0; i < changes; ++i) {
      unsigned off, val;
      in >> off >> val;
      assert(off >= 24 && off < 0x920);
      expected[off - 24] = val;
    }
    unsigned eventCount;
    in >> eventCount;
    std::vector<std::string> events(eventCount);
    for (auto &e : events)
      in >> e;
    auto adc = unhex(tableHex);
    unsigned char adcArray[40], dac[24]{}, eq[16]{};
    assert(adc.size() == 40);
    std::copy(adc.begin(), adc.end(), adcArray);
    RouterSlotTables tables(adcArray, dac, eq);
    state.slotTables = &tables;
    Context context;
    context.state = &state;
    Response response;
    IO io;
    Fixture router(state, response, io);
    context.router = &router;
    active = &context;
    if (name == "set2TrackInputRoute")
      router.set2TrackInputRoute(args[0], args[1]);
    else if (name == "setGEQToFWRoute")
      router.setGEQToFWRoute(args[0], args[1]);
    else if (name == "setMixerMuteInputRoute")
      router.setMixerMuteInputRoute(args[0], args[1]);
    else if (name == "setInputToAvbTxRoute")
      router.setInputToAvbTxRoute(args[0], args[1], args[2], args[3]);
    else if (name == "setInputToDanteTxRoute")
      router.setInputToDanteTxRoute(args[0], args[1], args[2], args[3],
                                    args[4]);
    else {
      assert(name == "setTalkbackToAvbTxRoute");
      router.setTalkbackToAvbTxRoute(args[0], args[1], args[2]);
    }
    assert(state.applicationBytes == expected);
    assert(context.events == events);
    assert(context.depth == 0 && context.packets.empty());
    active = nullptr;
    ++cases;
  }
  std::cout << "{\"passed\":true,\"six_setter_cases\":" << cases
            << ",\"actual_device_operations\":0}\n";
}
