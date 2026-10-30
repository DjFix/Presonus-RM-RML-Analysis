#include "presonus/noaa/router.hpp"
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
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
struct ScriptEnvironment {
  std::string home, fixture;
  bool nullHome = false, opened = true;
  FILE *file = nullptr;
  unsigned opens = 0, closes = 0;
  long position = 0;
};
static ScriptEnvironment *scriptEnvironment;
extern "C" char *__real_getenv(const char *);
extern "C" char *__wrap_getenv(const char *name) {
  if (!scriptEnvironment || std::strcmp(name, "HOME") != 0)
    return __real_getenv(name);
  return scriptEnvironment->nullHome ? nullptr : scriptEnvironment->home.data();
}
extern "C" FILE *__real_fopen(const char *, const char *);
extern "C" FILE *__wrap_fopen(const char *path, const char *mode) {
  if (!scriptEnvironment)
    return __real_fopen(path, mode);
  assert(active && std::strcmp(mode, "r+b") == 0);
  ++scriptEnvironment->opens;
  active->events.emplace_back(
      "open:" +
      hexBytes(reinterpret_cast<const unsigned char *>(path),
               std::strlen(path)) +
      ":3");
  if (!scriptEnvironment->opened)
    return nullptr;
  assert(!scriptEnvironment->file);
  scriptEnvironment->file =
      __real_fopen(scriptEnvironment->fixture.c_str(), "r+b");
  assert(scriptEnvironment->file);
  return scriptEnvironment->file;
}
extern "C" int __real_fclose(FILE *);
extern "C" int __wrap_fclose(FILE *file) {
  if (scriptEnvironment && file == scriptEnvironment->file) {
    scriptEnvironment->position = std::ftell(file);
    ++scriptEnvironment->closes;
    scriptEnvironment->file = nullptr;
  }
  return __real_fclose(file);
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  assert(active);
  va_list args;
  va_start(args, fmt);
  if (std::strcmp(fmt, "error parsing line %d.  %s\n") == 0) {
    const auto line = static_cast<std::uint32_t>(va_arg(args, int));
    const auto *text = va_arg(args, const char *);
    active->events.emplace_back(
        "parse_error:" + std::to_string(line) + ":" +
        hexBytes(reinterpret_cast<const unsigned char *>(text),
                 std::strlen(text)));
  } else if (std::strcmp(
                 fmt,
                 "routeScript: file exists but couldn't be opened: %s\n") ==
             0) {
    const auto *text = va_arg(args, const char *);
    active->events.emplace_back(
        "open_error:" + hexBytes(reinterpret_cast<const unsigned char *>(text),
                                 std::strlen(text)));
  } else {
    assert(
        std::strcmp(
            fmt,
            "DestID %d; Dest Channel %d; SourceID %d; Source Channel %d\n") ==
        0);
    std::string event = "notice";
    for (unsigned i = 0; i < 4; ++i)
      event +=
          ":" + std::to_string(static_cast<std::uint32_t>(va_arg(args, int)));
    active->events.push_back(event);
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

extern "C" void __real__ZN8Presonus4NOAA11TCardRouter14doRouteCommandEhhhhh(
    TCardRouter *, unsigned char, unsigned char, unsigned char, unsigned char,
    unsigned char);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter14doRouteCommandEhhhhh(
    TCardRouter *router, unsigned char d0, unsigned char c0, unsigned char d1,
    unsigned char c1, unsigned char remap) {
  assert(active && router == active->router && remap == 1);
  active->events.emplace_back("route:" + std::to_string(d0) + ":" +
                              std::to_string(c0) + ":" + std::to_string(d1) +
                              ":" + std::to_string(c1) + ":" +
                              std::to_string(remap));
  const auto old = observe;
  observe = false;
  try {
    __real__ZN8Presonus4NOAA11TCardRouter14doRouteCommandEhhhhh(router, d0, c0,
                                                                d1, c1, remap);
  } catch (...) {
    observe = old;
    throw;
  }
  observe = old;
}
static std::string rawText(const std::string &hex) {
  if (hex == "-" || hex == "NONE")
    return {};
  const auto data = unhex(hex);
  return std::string(data.begin(), data.end());
}
int main(int argc, char **argv) {
  assert(argc == 3);
  std::ifstream input(argv[1]);
  assert(input);
  std::string line;
  unsigned cases = 0, routePackets = 0, actualOpens = 0, actualCloses = 0;
  while (std::getline(input, line)) {
    std::istringstream in(line);
    std::string contentHex, tableHex, homeHex, nameHex;
    unsigned opened;
    long position;
    in >> contentHex >> tableHex >> homeHex >> nameHex >> opened >> position;
    assert(in && opened <= 1);
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
    const auto content = rawText(contentHex);
    std::string fixture = std::string(argv[2]) + "/script-fixture.txt";
    {
      std::ofstream file(fixture, std::ios::binary | std::ios::trunc);
      assert(file);
      file.write(content.data(), content.size());
      assert(file);
    }
    RouterState state;
    for (unsigned i = 0; i < state.applicationBytes.size(); ++i)
      state.applicationBytes[i] = static_cast<unsigned char>(cases + i * 29);
    const auto expected = state.applicationBytes;
    assert(tableHex.size() == 128);
    auto adc = unhex(tableHex.substr(0, 80)),
         dac = unhex(tableHex.substr(80, 48));
    unsigned char adcArray[40], dacArray[24], eqArray[16]{};
    std::copy(adc.begin(), adc.end(), adcArray);
    std::copy(dac.begin(), dac.end(), dacArray);
    RouterSlotTables tables(adcArray, dacArray, eqArray);
    state.slotTables = &tables;
    Context context;
    context.state = &state;
    Response response;
    IO io;
    Fixture router(state, response, io);
    context.router = &router;
    active = &context;
    ScriptEnvironment environment;
    environment.home = rawText(homeHex);
    environment.nullHome = homeHex == "NONE";
    environment.fixture = fixture;
    environment.opened = opened != 0;
    const auto name = rawText(nameHex);
    scriptEnvironment = &environment;
    router.routeScript(nameHex == "NONE" ? nullptr : name.c_str());
    assert(!environment.file && environment.opens == 1 &&
           environment.closes == opened && environment.position == position);
    assert(context.events == events);
    assert(state.applicationBytes == expected);
    assert(context.packets.size() == packets.size());
    for (unsigned i = 0; i < packets.size(); ++i) {
      assert(context.packets[i].length == packets[i].size());
      assert(std::equal(packets[i].begin(), packets[i].end(),
                        context.packets[i].bytes.begin()));
      ++routePackets;
    }
    assert(context.depth == 0);
    scriptEnvironment = nullptr;
    active = nullptr;
    ++cases;
    actualOpens += opened;
    actualCloses += environment.closes;
  }
  std::cout << "{\"passed\":true,\"script_cases\":" << cases
            << ",\"actual_route_packets\":" << routePackets
            << ",\"actual_local_file_opens\":" << actualOpens
            << ",\"actual_local_file_closes\":" << actualCloses
            << ",\"actual_device_operations\":0}\n";
}
