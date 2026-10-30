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
  if (std::strcmp(fmt, "!!!!!!!!!!!!!!! missed Route\n") == 0)
    active->events.emplace_back("capacity_error");
  else {
    assert(
        std::strcmp(
            fmt,
            "NOAA:route err found. destID:%d destch:%d srcID:%d srcch:%d\n") ==
        0);
    va_list args;
    va_start(args, fmt);
    std::string event = "single_error";
    for (int i = 0; i < 4; ++i)
      event += ":" + std::to_string(va_arg(args, int));
    va_end(args);
    active->events.push_back(event);
  }
  if (active->probe)
    probeLock();
  if (active->throwLog)
    throw std::runtime_error("diagnostic boundary failure");
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
  std::vector<unsigned char> result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result.push_back(
        static_cast<unsigned char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return result;
}
static void sourceLockCases() {
  RouterState state{};
  Response response;
  IO io;
  Fixture receiver(state, response, io);
  Context context;
  context.state = &state;
  context.router = &receiver;
  context.probe = true;
  active = &context;
  // Recursive same-thread source CCL mutex, with another thread blocked.
  state.lock.lock();
  assert(receiver.addIdleRoute(1, 2, 3, 4));
  state.lock.unlock();
  assert(context.depth == 0);
  context.reenter = true;
  store(state, 60);
  state.applicationBytes[256] = 1;
  receiver.idle();
  assert(context.reentries == 1 && state.applicationBytes[256] == 1 &&
         load(state) == 1);
  assert(context.packets.size() == 2 && context.packets[0].length == 239 &&
         context.packets[1].length == 7);
  context.reenter = false;
  context.throwPost = true;
  bool threw = false;
  try {
    receiver.idle();
  } catch (const std::runtime_error &) {
    threw = true;
  }
  assert(threw && context.depth == 0 && state.applicationBytes[256] == 0 &&
         load(state) == 0);
  probeLock();
  context.throwPost = false;
  context.throwLog = true;
  store(state, 512);
  threw = false;
  try {
    receiver.addIdleRoute(0, 0, 0, 0);
  } catch (const std::runtime_error &) {
    threw = true;
  }
  assert(threw && context.depth == 0 && load(state) == 512);
  probeLock();
  context.throwLog = false;
  for (std::uint32_t bits : {0xffffffbdu, 0x80000200u}) {
    store(state, bits);
    threw = false;
    try {
      receiver.addIdleRoute(1, 2, 3, 4);
    } catch (const std::out_of_range &) {
      threw = true;
    }
    assert(threw && context.depth == 0 && load(state) == bits);
  }
  store(state, 513);
  state.applicationBytes[256] = 1;
  threw = false;
  try {
    receiver.idle();
  } catch (const std::out_of_range &) {
    threw = true;
  }
  assert(threw && context.depth == 0 && load(state) == 513 &&
         state.applicationBytes[256] == 1);
  active = nullptr;
  std::cout << "{\"passed\":true,\"actual_ccl_recursive_reentrancy_unwind\":"
               "true,\"cross_thread_lock_probes\":"
            << context.probes << ",\"independent_guard_cases\":3}\n";
}
int main(int argc, char **argv) {
  if (argc > 1 && std::strcmp(argv[1], "--source-locks") == 0) {
    sourceLockCases();
    return 0;
  }
  std::ifstream file;
  if (argc > 1) {
    file.open(argv[1]);
    assert(file);
    std::cin.rdbuf(file.rdbuf());
  }
  unsigned cases = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string kind, appHex, eventString;
    std::int64_t count, overrideValue;
    unsigned flag, hasOverride, seed, a[5], expectedReturn, packetCount;
    RouterState state{};
    Response response;
    IO io;
    Fixture receiver(state, response, io);
    Context context;
    context.state = &state;
    context.router = &receiver;
    in >> kind >> count >> flag >> hasOverride >> overrideValue;
    for (auto &v : a)
      in >> v;
    in >> seed >> context.tickBase >> context.ack >> context.status >>
        expectedReturn >> appHex >> packetCount;
    assert(!in.fail());
    std::vector<std::pair<std::vector<unsigned char>, std::int64_t>>
        expectedPackets;
    for (unsigned i = 0; i < packetCount; ++i) {
      std::string hex;
      std::int64_t stamp;
      in >> hex >> stamp;
      expectedPackets.emplace_back(unhex(hex), stamp);
    }
    in >> eventString;
    assert(!in.fail());
    for (std::size_t i = 0; i < state.applicationBytes.size(); ++i)
      state.applicationBytes[i] =
          static_cast<unsigned char>(seed + (i + 24) * 29);
    state.applicationBytes[256] = static_cast<unsigned char>(flag);
    store(state, static_cast<std::uint32_t>(count));
    context.overrideCount = hasOverride;
    context.count = static_cast<std::uint32_t>(overrideValue);
    active = &context;
    if (kind == "add")
      assert(receiver.addIdleRoute(a[0], a[1], a[2], a[3]) ==
             bool(expectedReturn));
    else if (kind == "idle")
      receiver.idle();
    else {
      assert(kind == "single");
      receiver.doRouteCommand(a[0], a[1], a[2], a[3], a[4]);
    }
    auto expectedApp = unhex(appHex);
    assert(expectedApp.size() == state.applicationBytes.size() &&
           std::equal(expectedApp.begin(), expectedApp.end(),
                      state.applicationBytes.begin()));
    assert(context.depth == 0 &&
           context.packets.size() == expectedPackets.size());
    for (std::size_t i = 0; i < context.packets.size(); ++i) {
      const auto &p = context.packets[i];
      const auto &e = expectedPackets[i];
      assert(p.length == e.first.size() &&
             std::equal(e.first.begin(), e.first.end(), p.bytes.begin()));
      assert(p.portableMetadata().constructedQuotient == e.second);
    }
    std::string actualEvents;
    for (const auto &event : context.events)
      actualEvents += (actualEvents.empty() ? "" : ",") + event;
    if (actualEvents.empty())
      actualEvents = "-";
    assert(actualEvents == eventString);
    ++cases;
    active = nullptr;
  }
  std::cout << "{\"passed\":true,\"original_safe_cases\":" << cases << "}\n";
}
