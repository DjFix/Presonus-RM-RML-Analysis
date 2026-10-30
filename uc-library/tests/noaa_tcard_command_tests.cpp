#include "presonus/noaa/card.hpp"
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <type_traits>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::int64_t tick;
static unsigned clocks, ack;
static bool provider;
static std::string trace;
static CardState *currentState;
static std::array<unsigned char, 8> expectedShadow;
static unsigned posts, pumps, transfers;
static std::string hex(const unsigned char *p, std::size_t n) {
  static const char *d = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    s += d[p[i] >> 4];
    s += d[p[i] & 15];
  }
  return s;
}
static auto unhex(const std::string &s) {
  std::vector<unsigned char> p;
  assert(s.size() % 2 == 0);
  for (std::size_t i = 0; i < s.size(); i += 2)
    p.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return p;
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  assert(clocks < 2 && currentState->commandShadow == expectedShadow);
  return tick + std::int64_t(clocks++) * 1000003;
}
} // namespace presonus::dice
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  va_list args;
  va_start(args, format);
  if (std::string(format) == "NOAA: %s\n") {
    auto *s = va_arg(args, const char *);
    assert(s && *s);
    trace +=
        "N:" + hex(reinterpret_cast<const unsigned char *>(s), std::strlen(s)) +
        ";";
  } else {
    assert(std::string(format) == "TCARD: Setting clock source to %d\n");
    trace += "C:" + std::to_string(va_arg(args, int)) + ";";
  }
  va_end(args);
}
static SysexReceiver *receiver;
extern "C" unsigned char
__real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *, long long);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *self,
                                                  long long timeout) {
  assert(self == receiver && timeout == 500);
  trace += "W;";
  if (provider)
    return __real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(self, timeout);
  self->portableState().command = ack;
  return ack;
}
static unsigned expectedLength;
static std::string expectedBytes;
static std::int64_t expectedTimestamp;
struct Fixture final : TCard {
  using TCard::TCard;
  void receive(const SysexPacket &) override { std::abort(); }
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &packet) override {
    ++posts;
    assert(packet.length == expectedLength &&
           hex(packet.bytes.data(), packet.length) == expectedBytes &&
           clocks == 2);
    assert((packet.portableMetadata().headerWords ==
            std::array<std::uint32_t, 2>{}));
    assert((packet.portableMetadata().trailingWords ==
            std::array<std::uint32_t, 4>{}));
    assert(packet.portableMetadata().constructedQuotient == expectedTimestamp);
    for (unsigned i = packet.length; i < 255; ++i)
      assert(packet.bytes[i] == 0x45);
    assert(currentState->commandShadow == expectedShadow);
    trace += "P;";
    if (provider)
      SysexReceiver::post(packet);
    else {
      portableState().command = 0;
      portableState().status = 0;
      portableState().infoWords[0] = 0;
    }
  }
};
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool force) override {
    assert(!force && receiver);
    ++pumps;
    receiver->portableState().command = ack;
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  int transfer(int fd, const SpiTransfer &t) override {
    assert(provider && fd == 71 && t.length == expectedLength &&
           hex(t.tx, t.length) == expectedBytes);
    ++transfers;
    t.rx[0] = 0xf8;
    return 1;
  }
  std::int64_t rawTicks() override {
    assert(provider);
    return 4500000;
  }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
static_assert(std::is_abstract_v<TCard>);
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  IO io;
  CardState state{};
  currentState = &state;
  Fixture card(cardSetupTag, state, response, io);
  receiver = &card;
  std::string kind;
  unsigned cases = 0;
  const char *notices[] = {nullptr, "", "notice %n", "line\nending"};
  while (input >> kind) {
    long long a;
    unsigned b;
    std::string seed, shadow, expectedTrace;
    input >> a >> b >> ack >> tick >> seed >> shadow >> expectedLength >>
        expectedBytes >> expectedTimestamp >> expectedTrace;
    assert(ack < 256);
    auto raw = unhex(seed), out = unhex(shadow);
    assert(raw.size() == 8 && out.size() == 8);
    std::copy(raw.begin(), raw.end(), state.commandShadow.begin());
    std::copy(out.begin(), out.end(), expectedShadow.begin());
    clocks = 0;
    posts = 0;
    trace.clear();
    unsigned char result;
    if (kind == "command")
      result = card.doCommand(static_cast<unsigned char>(a), notices[b]);
    else if (kind == "clock")
      result = card.setClockSource(static_cast<int>(a));
    else {
      assert(kind == "geq");
      result = card.geqInit(a, b);
    }
    assert(result == ack && posts == 1 && clocks == 2 &&
           state.commandShadow == expectedShadow && trace == expectedTrace);
    ++cases;
  }
  assert(input.eof() && cases == 67076);
  // Actual borrowed SPI singleton plus actual CCL response pump/clock/sleep.
  // IO is injected before construction, no GPIO-owning default ctor is used.
  auto *previousIO = setSpiServiceConstructionIO(&io);
  SpiPacketState spiState(std::array<unsigned char, 256>{}, 0, 0, 0);
  {
    TCardSPI spi(spiState);
    auto *previousSingleton = SpiServiceAccess::singleton();
    SpiServiceAccess::singleton(&spi);
    SpiServiceAccess::bind(spi, io, 71, {}, 0);
    provider = true;
    for (unsigned which = 0; which < 3; ++which) {
      clocks = posts = 0;
      tick = -1000001;
      expectedTimestamp = 0;
      ack = 85;
      trace.clear();
      expectedShadow = state.commandShadow;
      if (which == 0) {
        expectedLength = 3;
        expectedBytes = "f015f7";
      } else if (which == 1) {
        expectedLength = 5;
        expectedBytes = "f0280f0ff7";
      } else {
        expectedLength = 7;
        expectedBytes = "f01c017f0101f7";
        auto bytes = unhex(expectedBytes);
        std::copy(bytes.begin(), bytes.end(), expectedShadow.begin());
      }
      auto result = which == 0   ? card.doCommand(0x95, nullptr)
                    : which == 1 ? card.setClockSource(-1)
                                 : card.geqInit(255, 129);
      assert(result == 85 && posts == 1 && clocks == 2);
    }
    SpiServiceAccess::singleton(previousSingleton);
    provider = false;
  }
  setSpiServiceConstructionIO(previousIO);
  assert(pumps == 3 && transfers == 3);
  std::cout << "{\"passed\":true,\"original_cases\":" << cases
            << ",\"ack_byte_domain\":256,\"two_signed_packet_clocks\":true,"
               "\"shadow_eighth_byte_preserved\":true,\"real_spi_ccl_response_"
               "cases\":3,\"physical_operations\":0}\n";
}
