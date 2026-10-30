#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/noaa/card.hpp"
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
using namespace Presonus;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::string trace;
static std::int64_t tick;
static unsigned clocks, posts, waits, pumps, transfers;
static bool provider;
static std::array<unsigned, 2> acks;
struct Packet {
  unsigned length;
  std::string bytes;
  std::int64_t timestamp;
};
static std::vector<Packet> packets;
static std::string hex(const unsigned char *p, std::size_t n) {
  static const char *d = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    s += d[p[i] >> 4];
    s += d[p[i] & 15];
  }
  return s;
}
static std::string hex(const char *s) {
  return hex(reinterpret_cast<const unsigned char *>(s), std::strlen(s));
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  assert(clocks < 4);
  return tick + std::int64_t(clocks++) * 1000003;
}
} // namespace presonus::dice
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  trace += "D:" + hex(format);
  va_list ap;
  va_start(ap, format);
  std::string fmt(format);
  if (fmt == " Card Type:%d (%s)\n") {
    trace += ":" + std::to_string(va_arg(ap, int));
    auto *s = va_arg(ap, const char *);
    trace += ":" + (s ? "s" + hex(s) : "NULL");
  } else if (fmt == "DeviceID #:0x%2X\n") {
    trace += ":" + std::to_string(va_arg(ap, unsigned));
  } else {
    unsigned count = 0;
    for (std::size_t i = 0; i + 1 < fmt.size(); ++i)
      if (fmt[i] == '%' && fmt[i + 1] == 'd')
        ++count;
    if (fmt.find("%08x") != std::string::npos) {
      for (unsigned i = 0; i < 2; ++i)
        trace += ":" + std::to_string(va_arg(ap, unsigned));
    } else
      for (unsigned i = 0; i < count; ++i)
        trace += ":" + std::to_string(va_arg(ap, int));
  }
  va_end(ap);
  trace += ';';
}
static SysexReceiver *receiver;
extern "C" unsigned char
__real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *, long long);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *self,
                                                  long long timeout) {
  assert(self == receiver && timeout == 500 && waits < packets.size());
  auto ack = acks[waits++];
  trace += "W:" + std::to_string(ack) + ";";
  if (provider)
    return __real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(self, timeout);
  self->portableState().command = ack;
  return ack;
}
struct Fixture final : TCard {
  using TCard::TCard;
  void receive(const SysexPacket &) override { std::abort(); }
  bool updateFirmware(UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &packet) override {
    assert(posts < packets.size());
    const auto &expected = packets[posts++];
    assert(packet.length == expected.length &&
           hex(packet.bytes.data(), packet.length) == expected.bytes &&
           packet.portableMetadata().constructedQuotient == expected.timestamp);
    assert((packet.portableMetadata().headerWords ==
            std::array<std::uint32_t, 2>{}));
    assert((packet.portableMetadata().trailingWords ==
            std::array<std::uint32_t, 4>{}));
    for (unsigned i = packet.length; i < 255; ++i)
      assert(packet.bytes[i] == 0x45);
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
    assert(!force && waits);
    ++pumps;
    receiver->portableState().command = acks[waits - 1];
  }
};
struct IO final : SpiServiceIO {
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  int transfer(int fd, const SpiTransfer &t) override {
    assert(provider && fd == 71 && posts &&
           t.length == packets[posts - 1].length &&
           hex(t.tx, t.length) == packets[posts - 1].bytes);
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
  std::array<std::unique_ptr<ResourceLibrary>, 5> libs;
  const char *names[] = {"NOAA_S800ARM", "NOAA_S800FPGA", "NIMH_ARM",
                         "NIMH_FPGA",    "ESA_ARM",       "ESA_FPGA"};
  static const unsigned char dummy = 0;
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  IO io;
  CardState state{};
  Fixture card(cardSetupTag, state, response, io);
  receiver = &card;
  std::string kind;
  unsigned cases = 0, rateCases = 0, macCases = 0, statusCases = 0;
  while (input >> kind) {
    if (kind == "L") {
      unsigned index;
      input >> index;
      libs[index] = std::make_unique<ResourceLibrary>();
      for (auto *name : names) {
        unsigned present, value;
        input >> present >> value;
        if (present)
          libs[index]->addFirmware(name, value, &dummy, 1, false);
      }
      continue;
    }
    trace.clear();
    clocks = posts = waits = 0;
    packets.clear();
    std::string expectedTrace;
    if (kind == "R") {
      long long rate, link;
      unsigned result, n;
      input >> state.observedWord3c >> rate >> link >> tick >> acks[0] >>
          acks[1] >> result >> n;
      for (unsigned i = 0; i < n; ++i) {
        Packet p;
        input >> p.length >> p.bytes >> p.timestamp;
        packets.push_back(p);
      }
      input >> expectedTrace;
      assert(card.sendSampleRate(int(rate), int(link)) == result &&
             posts == n && waits == n && clocks == n * 2);
      ++rateCases;
    } else if (kind == "M") {
      unsigned serial, result;
      input >> serial >> result >> expectedTrace;
      assert(card.generateAlternateMac(serial) == result && clocks == 0 &&
             posts == 0 && waits == 0);
      ++macCases;
    } else {
      assert(kind == "S");
      unsigned lib;
      input >> lib >> state.observedWord14 >> state.observedWord18 >>
          state.observedWord1c >> state.observedWord20 >>
          state.observedWord24 >> state.observedWord28 >>
          state.observedWord34 >> state.observedWord38 >>
          state.observedWord3c >> state.observedWord40 >>
          state.observedWord44 >> state.observedWord4c >>
          state.observedWord50 >> state.observedWord54 >>
          state.observedWord58 >> expectedTrace;
      assert(lib < 5 && libs[lib]);
      state.resources = libs[lib].get();
      card.printStatus();
      assert(clocks == 0 && posts == 0 && waits == 0);
      ++statusCases;
    }
    if (trace != expectedTrace) {
      std::cerr << "Mismatch case" << cases << " kind" << kind << "\nACTUAL "
                << trace << "\nEXPECTED " << expectedTrace << '\n';
      return 1;
    }
    ++cases;
  }
  assert(input.eof() && rateCases > 65000 && macCases > 4000 &&
         statusCases == 160);
  // Five independently pinned original register-trace regressions, including
  // argument order and final field-width truncation; no numeric bug fix.
  const std::pair<unsigned, unsigned> pinned[] = {{0u, 300000u},
                                                  {12345678u, 34425678u},
                                                  {70000000u, 100000u},
                                                  {99999999u, 99129999u},
                                                  {4294967295u, 94729672u}};
  for (auto regression : pinned) {
    trace.clear();
    clocks = posts = waits = 0;
    assert(card.generateAlternateMac(regression.first) == regression.second);
    assert(clocks == 0 && posts == 0 && waits == 0);
  }
  // Genuine existing SPI and CCL response paths for ordinary and workaround
  // cases. Borrowed singleton is restored before destruction; no owned GPIO IO.
  auto *previousIO = setSpiServiceConstructionIO(&io);
  SpiPacketState spiState(std::array<unsigned char, 256>{}, 0, 0, 0);
  {
    TCardSPI spi(spiState);
    auto *previous = SpiServiceAccess::singleton();
    SpiServiceAccess::singleton(&spi);
    SpiServiceAccess::bind(spi, io, 71, {}, 0);
    provider = true;
    for (unsigned board : {22u, 23u, 24u}) {
      state.observedWord3c = board;
      clocks = posts = waits = 0;
      tick = -1000001;
      acks = {85, 97};
      packets.clear();
      if (board != 22)
        packets.push_back({4, "f02101f7", 0});
      packets.push_back({5, "f0117f01f7", board == 22 ? 0 : 2});
      assert(card.sendSampleRate(255, 129) == (board == 22 ? 85 : 97));
    }
    SpiServiceAccess::singleton(previous);
    provider = false;
  }
  setSpiServiceConstructionIO(previousIO);
  assert(pumps == 5 && transfers == 5);
  std::cout << "{\"passed\":true,\"original_cases\":" << cases
            << ",\"rate_cases\":" << rateCases << ",\"mac_cases\":" << macCases
            << ",\"status_cases\":" << statusCases
            << ",\"pinned_mac_regressions\":5,\"actual_ccl_strings\":true,"
               "\"real_spi_ccl_response_cases\":3,"
               "\"physical_operations\":0}\n";
}
