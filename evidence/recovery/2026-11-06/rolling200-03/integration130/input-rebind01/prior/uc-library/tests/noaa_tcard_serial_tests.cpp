#include "presonus/noaa/card.hpp"
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::int64_t tick, timestamp;
static unsigned clocks, ack, transfers, waits, timeouts;
static std::string expectedBytes, trace;
static SysexReceiver *receiver;
static bool provider;
static bool deliverAtSleep;
static std::string hex(const unsigned char *p, unsigned n) {
  constexpr char digits[] = "0123456789abcdef";
  std::string out;
  for (unsigned i = 0; i < n; ++i) {
    out += digits[p[i] >> 4];
    out += digits[p[i] & 15];
  }
  return out;
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  assert(clocks < 2);
  trace += "clock;";
  return tick + std::int64_t(clocks++) * 1000003;
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  const std::string f = format;
  if (f == "programming serial reset\n")
    trace += "debug;";
  else if (f == "Generated alternate AVB MAC %d from %d\n")
    trace += "alternate_debug;";
  else if (f == "ack timeout\n")
    ++timeouts;
  else
    std::abort();
}
extern "C" void
__wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned milliseconds) {
  if (milliseconds == 4000) {
    trace += "sleep4000;";
    if (deliverAtSleep) {
      SysexPacket p;
      p.length = 4;
      p.bytes[0] = 0xf0;
      p.bytes[1] = static_cast<unsigned char>(ack);
      p.bytes[3] = 0xf7;
      receiver->SysexReceiver::receive(p);
    }
  } else
    assert(provider && milliseconds == 1); // finite wait import; no real sleep
}
extern "C" unsigned char
__real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *, long long);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *self,
                                                  long long timeout) {
  assert(self == receiver && timeout == 500);
  trace += "wait500;";
  ++waits;
  return provider
             ? __real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(self, timeout)
             : ack;
}
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool force) override {
    assert(provider);
    if (ack) {
      const unsigned char bytes[] = {0xf0, static_cast<unsigned char>(ack), 0,
                                     0xf7};
      // Deliver through the genuine response parser. Application acceptance is
      // a separate, already tested boundary; no hardware response is implied.
      SysexPacket p;
      std::copy_n(bytes, 4, p.bytes.begin());
      p.length = 4;
      receiver->SysexReceiver::receive(p);
    } else
      (void)force;
  }
};
struct Pins final : presonus::surface_panel_port::InputPinIO {
  std::FILE *open(const char *, const char *) override { return nullptr; }
  void log(const char *) override {}
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override { std::abort(); }
  void formatPath(char *, std::size_t, const char *, int) override {
    std::abort();
  }
  std::size_t write(const void *, std::size_t, std::size_t,
                    std::FILE *) override {
    std::abort();
  }
  int buffering(std::FILE *, char *, int, std::size_t) override {
    std::abort();
  }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { return 4500000; }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
  int transfer(int fd, const SpiTransfer &t) override {
    assert(fd == 71 && t.length == 14 && hex(t.tx, t.length) == expectedBytes);
    ++transfers;
    t.rx[0] = 0xf8;
    return 1;
  }
};
struct Concrete final : TCard {
  using TCard::TCard;
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &p) override {
    assert(clocks == 2 && p.length == 14 &&
           hex(p.bytes.data(), 14) == expectedBytes);
    assert(p.portableMetadata().constructedQuotient == timestamp);
    assert(
        (p.portableMetadata().headerWords == std::array<std::uint32_t, 2>{}));
    assert(
        (p.portableMetadata().trailingWords == std::array<std::uint32_t, 4>{}));
    for (unsigned i = 14; i < 255; ++i)
      assert(p.bytes[i] == 0x45);
    trace += "post;";
    SysexReceiver::post(p); // genuine production packet, lock and SPI providers
  }
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream in(argv[1]);
  assert(in);
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  IO io;
  static Pins pins;
  presonus::surface_panel_port::setInputPinConstructionIO(&pins);
  setSpiServiceConstructionIO(&io);
  SpiPacketState spiState({}, 0, 0, 0);
  TCardSPI spi(spiState);
  SpiServiceAccess::bind(spi, io, 71, {}, 0);
  SpiServiceAccess::singleton(&spi);
  CardState state{};
  Concrete card(cardSetupTag, state, response, io);
  receiver = &card;
  struct OwnedFixture {
    std::int64_t tick, timestamp;
    unsigned word30;
    std::string bytes, events;
  } ownedFixture{};
  unsigned type, serial, word30, cases = 0;
  std::string events;
  while (in >> type >> serial >> word30 >> tick >> ack >> expectedBytes >>
         timestamp >> events) {
    if (type == 1 && serial == 0xffffffffu && ack == 255)
      ownedFixture = {tick, timestamp, word30, expectedBytes, events};
    state.observedWord14 = type;
    state.expectedSerial = serial;
    state.observedWord30 = word30;
    for (bool actual : {false, true}) {
      provider = actual;
      clocks = 0;
      trace.clear();
      card.portableState().command = 71;
      auto before = transfers;
      unsigned t = timeouts;
      assert(card.programSerialReset() == ack);
      assert(trace == events + ";" && clocks == 2 && transfers == before + 1);
      assert(timeouts == t + (actual && ack == 0 ? 1 : 0));
      assert(state.observedWord14 == type && state.expectedSerial == serial &&
             state.observedWord30 == word30);
      ++cases;
    }
  }
  // A real default-owned caller binds typed dependencies through the public
  // independent API, then uses actual registration/SPI/CCL response providers.
  // Expected packet and clock metadata remain the original native fixture.
  assert(!ownedFixture.bytes.empty());
  {
    Concrete owned;
    receiver = &owned;
    auto &bound = owned.portableCardState();
    bound.expectedSerial = 0xffffffffu;
    bound.observedWord14 = 1;
    bound.observedWord30 = ownedFixture.word30;
    const Concrete &view = owned;
    assert(&view.portableCardState() == &bound);
    expectedBytes = ownedFixture.bytes;
    tick = ownedFixture.tick;
    timestamp = ownedFixture.timestamp;
    ack = 255;
    clocks = 0;
    trace.clear();
    provider = deliverAtSleep = true;
    const auto before = transfers;
    assert(owned.programSerialReset() == 255);
    assert(trace == ownedFixture.events + ";" && transfers == before + 1);
    assert(SpiServiceAccess::state(spi).receivers.contains(&owned));
    deliverAtSleep = false;
  }
  assert(SpiServiceAccess::state(spi).receivers.isEmpty());
  receiver = &card;
  // Explicit source-port precondition; opaque references never become serials.
  state.expectedSerial.reset();
  clocks = 0;
  bool rejected = false;
  try {
    card.programSerialReset();
  } catch (const std::logic_error &) {
    rejected = true;
  }
  assert(rejected && clocks == 0);
  SpiServiceAccess::singleton(nullptr);
  std::cout
      << cases
      << " serial replays; all native packets/metadata/order/byte returns; "
         "actual SPI and CCL response parser/clock/timeout exercised; "
         "default-owned public binding replay passed\n";
}
