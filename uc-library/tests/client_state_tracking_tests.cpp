#include "presonus/uc/client_event_values.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <time.h>
#include <vector>
// Fixture-only opaque completion for a production-forward-declared type.
// Its empty test representation is not recovered payload layout or fields;
// the original and reconstructed noop never inspect this object.
namespace Presonus::UC {} // namespace Presonus::UC
using namespace Presonus::UC;
using Access = presonus::uc::ClientStatePortAccess;
namespace test {
std::vector<std::string> events;
Event sent{};
bool clockSmoke = false;
unsigned sourceClockCalls = 0;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
std::string trace() {
  std::string s;
  for (auto &e : events) {
    if (!s.empty())
      s += ',';
    s += e;
  }
  return s;
}
} // namespace test
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
  int unregisterHandler(IEventHandler *) override { return 0; }
  int sendEvent(const Event &value, int flag) override {
    test::require(flag == 0, "transport flag changed");
    test::sent = value;
    test::events.push_back("network");
    return -7;
  }
  int sendMulticastEvent(const Event &) override { std::abort(); }
  int setMulticastMapping(int, int, unsigned char, unsigned char) override {
    std::abort();
  }
  int processIdle() override { std::abort(); }
  int getServerContextInfo(ServerContextInfo &, int) override { std::abort(); }
  int addExternalConnection(IConnection *&, IDataChannel *, int, unsigned char,
                            IEventHandler *) override {
    std::abort();
  }
  int updateExternalConnection(IDataChannel *, int) override { std::abort(); }
  int removeExternalConnection(IDataChannel *) override { std::abort(); }
  int rescanAll(unsigned char) override { std::abort(); }
  int resetConnection() override { std::abort(); }
  int addErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int removeErrorReporter(INetworkErrorReporter *) override { std::abort(); }
  int simulateConnectionErrors() override { std::abort(); }
  int waitForOutgoingEvents(int) override { std::abort(); }
  int suspendNetworkAdapters(unsigned char) override { std::abort(); }
  int isSendingFromExternalConnection(int) override { std::abort(); }
};
struct Client final : ClientImplementation {
  std::uint64_t now = 0;
  explicit Client(Transport &network)
      : ClientImplementation(presonus::uc::ClientStatePortTag{}, network,
                             0x11223344, 0xaabbccdd) {}
  std::uint64_t getSystemTime() const override {
    test::events.push_back("clock");
    return now;
  }
  int handleEvent(void *, const Event &) override { std::abort(); }
  void updateLevels(const MeterEvent &) override { std::abort(); }
  void receiveEvent(const TimeCodeEvent &) override { std::abort(); }
  void receiveEvent(const ParamEvent &) override { std::abort(); }
  void receiveEvent(const MessageEvent &) override { std::abort(); }
  void receiveEvent(const BinaryEvent &) override { std::abort(); }
  void receiveEvent(const DebugEvent &) override { std::abort(); }
  using ClientImplementation::receiveEvent;
  void sendAllToServer() override { std::abort(); }
};
extern "C" int __real_clock_gettime(clockid_t, timespec *);
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *out) {
  if (test::clockSmoke) {
    test::require(clock == CLOCK_MONOTONIC,
                  "actual CCL clock selected unexpected system source");
    out->tv_sec = 123;
    out->tv_nsec = 456000000;
    ++test::sourceClockCalls;
    return 0;
  }
  return __real_clock_gettime(clock, out);
}
struct Digest {
  std::uint64_t value = 14695981039346656037ULL;
  void append(std::uint64_t bits, unsigned bytes) {
    for (unsigned i = 0; i < bytes; ++i) {
      value ^= (bits >> (i * 8)) & 255;
      value *= 1099511628211ULL;
    }
  }
};
int main(int argc, char **argv) {
  try {
    test::require(argc == 2, "fixture missing");
    std::ifstream file(argv[1]);
    test::require(bool(file), "fixture unreadable");
    std::string line;
    Transport network;
    std::array<unsigned, 8> tokens{};
    auto context = [&](int id) -> void * {
      return id ? &tokens.at(id) : nullptr;
    };
    auto contextId = [&](void *p) -> unsigned {
      if (!p)
        return 0;
      for (unsigned i = 1; i < tokens.size(); ++i)
        if (p == &tokens[i])
          return i;
      throw std::runtime_error("unknown context identity");
    };
    unsigned cases = 0;
    while (std::getline(file, line)) {
      std::istringstream row(line);
      std::string role, action, expectedTrace;
      int count, timeout, which;
      std::uint64_t now, old, expectedDigest;
      std::uint32_t expectedResult;
      row >> role >> action >> count >> now >> old >> timeout >> which >>
          expectedResult >> expectedDigest >> expectedTrace;
      test::require(bool(row), "invalid fixture");
      Client client(network);
      client.now = now;
      Access::lastAlive(client) = old;
      Access::untouchedBits(client) = 0x0123456789abcdefULL;
      auto &changes = Access::changes(client);
      test::require(changes.getCapacity() == 64,
                    "actual fixed capacity differs");
      auto *cells = changes.getItems();
      for (unsigned i = 0; i < 64; ++i) {
        cells[i].context = context(i % 3);
        cells[i].opaqueWord = 0xabc00000 + i;
        cells[i].timeBits = old + std::uint64_t(i) * 17;
      }
      changes.setCount(count);
      Event event{0x10203040, 0x50607080, 0x90abcdef, 0xfedcba09};
      test::events.clear();
      test::sent = {};
      std::uint32_t result = 0;
      if (action == "has")
        result = client.hasParamChanged(context(which), timeout);
      else if (action == "reset_all")
        client.resetParamChanges();
      else if (action == "reset_ctx")
        client.resetParamChanges(context(which));
      else if (action == "set")
        client.setLastParamChange(context(which));
      else if (action == "mark")
        client.markAlive();
      else if (action == "keep")
        client.keepAlive();
      else if (action == "send")
        result = static_cast<std::uint32_t>(client.sendEvent(event));
      else {
        Event loopHeader{};
        LoopbackReplyEvent opaque{loopHeader};
        client.receiveEvent(opaque);
      }
      // Actual CCL removeAt is source-provided/inlined, not a fake provider.
      // Its logical effects, including every stale/opaque cell, are compared
      // below. Original Core boundary trace remove:index is not a native
      // external call.
      std::string observed = test::trace(), filtered;
      std::istringstream trace(expectedTrace);
      std::string item;
      while (std::getline(trace, item, ','))
        if (item != "-" && item.rfind("remove:", 0) != 0) {
          if (!filtered.empty())
            filtered += ',';
          filtered += item;
        }
      test::require(observed == filtered,
                    ("app clock/transport trace differs: " + observed +
                     " expected " + filtered)
                        .c_str());
      if (action == "has" || action == "send")
        test::require(result == expectedResult,
                      "defined return-bit projection differs");
      Digest hash;
      hash.append(changes.count(), 4);
      hash.append(Access::lastAlive(client), 8);
      hash.append(Access::untouchedBits(client), 8);
      for (unsigned i = 0; i < 64; ++i) {
        hash.append(contextId(cells[i].context), 4);
        hash.append(cells[i].opaqueWord, 4);
        hash.append(cells[i].timeBits, 8);
      }
      for (auto *value : {&event, &test::sent}) {
        hash.append(value->type, 4);
        hash.append(value->reserved04, 4);
        hash.append(value->routeA, 4);
        hash.append(value->routeB, 4);
      }
      test::require(hash.value == expectedDigest,
                    ("all64cell/count/time/event projection differs: " +
                     action + " count=" + std::to_string(count))
                        .c_str());
      ++cases;
    }
    test::require(cases == 13440, "wrong fixture count");
    test::clockSmoke = true;
    const auto milliseconds = presonus::uc::clientSystemMilliseconds();
    test::clockSmoke = false;
    test::require(milliseconds == 123456 && test::sourceClockCalls == 1,
                  "actual pinned CCL clock conversion/single syscall differs");
    std::cout << "PASS original_app_cases=" << cases
              << " all64_opaque_stale_cells=true capacity64=true "
                 "shared_last_alive=true unsigned_wrap_signed_time=true "
                 "route_backend_noop=true actual_CCL_clock_smoke=1\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
