#include "presonus/noaa/router.hpp"
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace presonus::noaa;
using namespace presonus::dice;
using namespace Presonus::NOAA;
static std::int64_t ticks[2];
static unsigned clockCalls;
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  assert(clockCalls < 2);
  return ticks[clockCalls++];
}
} // namespace presonus::dice
struct Response final : ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  unsigned errors = 0;
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool out, const char *message, int value, bool arg) override {
    assert(!out && std::strcmp(message, "route err found") == 0 && value == 0 &&
           !arg);
    ++errors;
  }
};
struct Fixture final : TCardRouter {
  Fixture(RouterState &s, Response &r, IO &io)
      : TCardRouter(s, r, io, rm13731LinkAddressRouterLookup()) {}
  SysexPacket observed;
  unsigned posts = 0;
  void post(SysexPacket &p) override {
    observed = p;
    ++posts;
    portableState().command = 0;
    portableState().status = 0;
  }
};
static Fixture *active;
static unsigned ack, status, waits;
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *receiver,
                                                  long long timeout) {
  assert(receiver == active && timeout == 500 && active->posts == 1);
  assert(receiver->portableState().command == 0 &&
         receiver->portableState().status == 0);
  ++waits;
  receiver->portableState().command = static_cast<unsigned char>(ack);
  receiver->portableState().status = static_cast<unsigned char>(status);
  return static_cast<unsigned char>(ack);
}
static std::vector<unsigned char> unhex(const std::string &s) {
  if (s == "-")
    return {};
  std::vector<unsigned char> bytes;
  assert(s.size() % 2 == 0);
  for (std::size_t i = 0; i < s.size(); i += 2)
    bytes.push_back(
        static_cast<unsigned char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return bytes;
}
int main(int argc, char **argv) {
  std::ifstream fixture;
  if (argc > 1) {
    fixture.open(argv[1]);
    assert(fixture);
    std::cin.rdbuf(fixture.rdbuf());
  }
  std::string line;
  unsigned routeCases = 0, acceptsCases = 0;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    char kind;
    in >> kind;
    RouterState state{};
    Response response;
    IO io;
    Fixture receiver(state, response, io);
    if (kind == 'A') {
      unsigned length, command, expected;
      in >> length >> command >> expected;
      SysexPacket packet;
      packet.length = static_cast<unsigned char>(length);
      packet.bytes[1] = static_cast<unsigned char>(command);
      ISysexReceiver *base = &receiver;
      assert(base->accepts(packet) == bool(expected));
      ++acceptsCases;
      continue;
    }
    assert(kind == 'R');
    int count, aliasOffset;
    unsigned flag, seed, expectedLength;
    std::int64_t expectedTime;
    std::string routeHex, appHex, packetHex;
    in >> count >> aliasOffset >> flag >> ack >> status >> seed >> ticks[0] >>
        ticks[1] >> routeHex >> appHex >> packetHex >> expectedLength >>
        expectedTime;
    assert(!in.fail());
    for (std::size_t i = 0; i < state.applicationBytes.size(); ++i)
      state.applicationBytes[i] =
          static_cast<unsigned char>(seed + (i + 24) * 29);
    auto routes = unhex(routeHex), expectedApp = unhex(appHex),
         expectedPacket = unhex(packetHex);
    clockCalls = waits = 0;
    active = &receiver;
    auto *input =
        count > 0 ? reinterpret_cast<DiceRoute *>(routes.data()) : nullptr;
    if (aliasOffset >= 0) {
      assert(static_cast<std::size_t>(aliasOffset) + routes.size() <=
             state.applicationBytes.size());
      std::copy(routes.begin(), routes.end(),
                state.applicationBytes.begin() + aliasOffset);
      input = reinterpret_cast<DiceRoute *>(state.applicationBytes.data() +
                                            aliasOffset);
    }

    receiver.doRouteCommands(input, count, static_cast<unsigned char>(flag));
    assert(clockCalls == 2 && waits == 1 && receiver.posts == 1);
    assert(std::equal(expectedApp.begin(), expectedApp.end(),
                      state.applicationBytes.begin()));
    assert(expectedApp.size() == state.applicationBytes.size());
    assert(receiver.observed.length == expectedLength &&
           expectedPacket.size() == expectedLength);
    assert(std::equal(expectedPacket.begin(), expectedPacket.end(),
                      receiver.observed.bytes.begin()));
    const auto &m = receiver.observed.portableMetadata();
    assert(m.headerWords == (std::array<std::uint32_t, 2>{0, 0}));
    assert(m.constructedQuotient == expectedTime);
    assert(m.trailingWords == (std::array<std::uint32_t, 4>{0, 0, 0, 0}));
    assert(io.errors == unsigned(!(ack && status)));
    ++routeCases;
  }
  RouterState state{};
  Response response;
  IO io;
  Fixture receiver(state, response, io);
  bool rejected = false;
  try {
    receiver.doRouteCommands(nullptr, 578, 1);
  } catch (const std::length_error &) {
    rejected = true;
  }
  assert(rejected && receiver.posts == 0 && io.errors == 0);
  rejected = false;
  try {
    receiver.doRouteCommands(nullptr, 1, 1);
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  assert(rejected && receiver.posts == 0 && io.errors == 0);
  std::cout << "{\"passed\":true,\"routes\":" << routeCases
            << ",\"accepts\":" << acceptsCases
            << ",\"independent_guard_cases\":2,\"physical_operations\":0}\n";
}
