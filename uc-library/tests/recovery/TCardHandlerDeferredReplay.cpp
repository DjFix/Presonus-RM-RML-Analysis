#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/router.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::vector<std::array<unsigned, 4>> calls;
static std::vector<std::vector<unsigned char>> packets;
static bool initializing;
static unsigned initializations, rates, acks;
namespace presonus::dice {
std::int64_t packetClockRawTicks() { return 1000000; }
} // namespace presonus::dice
extern "C" void
__real__ZN8Presonus4NOAA11TCardRouter10initRoutesEv(TCardRouter *);
extern "C" void
__wrap__ZN8Presonus4NOAA11TCardRouter10initRoutesEv(TCardRouter *r) {
  ++initializations;
  initializing = true;
  __real__ZN8Presonus4NOAA11TCardRouter10initRoutesEv(r);
  initializing = false;
}
extern "C" void __real__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(
    TCardRouter *, unsigned char, unsigned char, int, unsigned char);
extern "C" void __wrap__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(
    TCardRouter *r, unsigned char d, unsigned char s, int m, unsigned char b) {
  if (!initializing)
    calls.push_back({d, s, unsigned(m), b});
  __real__ZN8Presonus4NOAA11TCardRouter13setAVS48RouteEhhih(r, d, s, m, b);
}
extern "C" unsigned char
__real__ZN8Presonus4NOAA5TCard14sendSampleRateEii(TCard *, int, int);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA5TCard14sendSampleRateEii(TCard *r, int a, int b) {
  ++rates;
  return __real__ZN8Presonus4NOAA5TCard14sendSampleRateEii(r, a, b);
}
// Same-TU GEQ dispatch cannot be observed with linker --wrap; actual packet is
// the observable evidence that the existing body ran.
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *receiver,
                                                  long long t) {
  assert(t == 500);
  ++acks;
  receiver->portableState().status = 1;
  return 1;
}
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
static void capture(SysexPacket &p) {
  packets.emplace_back(p.bytes.begin(), p.bytes.begin() + p.length);
}
struct Card final : TCard {
  Card(CardState &s, Response &r, IO &i) : TCard(cardSetupTag, s, r, i) {}
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &p) override { capture(p); }
};
struct Router final : TCardRouter {
  Router(RouterState &s, Response &r, IO &i)
      : TCardRouter(s, r, i, rm13731LinkAddressRouterLookup()) {}
  void post(SysexPacket &p) override {
    capture(p);
    portableState().command = 0;
    portableState().status = 0;
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &s, Response &r)
      : TCardHandler(cardHandlerSetupTag, s, r) {}
  void setProperty(const Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
  int threadEntry() override { std::abort(); }
  void post(SysexPacket &p) override { capture(p); }
};
static int signedWord(unsigned n) {
  std::int32_t v;
  std::memcpy(&v, &n, 4);
  return v;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string line;
  unsigned cases = 0;
  while (std::getline(file, line)) {
    std::istringstream in(line);
    unsigned kind, word[6], code, n;
    in >> kind;
    for (auto &v : word)
      in >> v;
    in >> code >> n;
    std::vector<std::array<unsigned, 4>> expected(n);
    for (auto &a : expected)
      for (auto &v : a)
        in >> v;
    Response response;
    IO io;
    CardState cs{};
    cs.observedWord3c = 23;
    Card card(cs, response, io);
    RouterState rs{};
    rs.applicationBytes.fill(0);
    rs.slotTables = &rm13731GambitRouterSlots();
    Router router(rs, response, io);
    CardHandlerState hs{card};
    hs.router = &router;
    Handler handler(hs, response);
    Core::Property p(kind == 1   ? 1936225136
                     : kind == 2 ? 1399157877
                     : kind == 3 ? 1634038640
                                 : 0,
                     40);
    float f;
    std::memcpy(&f, word, 4);
    DeferredRateProjection rate{&p, f, signedWord(word[5])};
    hs.deferredRate = &rate;
    DeferredRouteProjection route{&p,
                                  word[0],
                                  signedWord(word[1]),
                                  signedWord(word[2]),
                                  signedWord(word[3]),
                                  signedWord(word[4])};
    hs.deferredRoutes = &route;
    std::array<unsigned char, 33> geq{};
    for (unsigned i = 0; i < 33; ++i)
      geq[i] = i + 128;
    hs.geqProperty = &p;
    hs.geqPayload = &geq;
    calls.clear();
    packets.clear();
    initializations = rates = acks = 0;
    handler.setPropertyDeferred(p);
    assert(calls == expected);
    assert(initializations == (kind == 3));
    assert(rates == (kind == 2));
    auto actualState = rs.applicationBytes;
    auto actualPackets = packets;
    if (kind == 3) {
      rs.applicationBytes.fill(0);
      packets.clear();
      router.initRoutes();
      for (auto a : expected)
        router.setAVS48Route(a[0], a[1], int(a[2]), a[3]);
      assert(rs.applicationBytes == actualState && packets == actualPackets);
    } else if (kind == 2) {
      assert(acks == 2 && packets.size() == 2);
      assert((packets[0] ==
              std::vector<unsigned char>{
                  240, 33, static_cast<unsigned char>(code > 1), 247}));
      assert(
          (packets[1] == std::vector<unsigned char>{
                             240, 17, static_cast<unsigned char>(code),
                             static_cast<unsigned char>(word[5] & 127), 247}));
    } else if (kind == 1) {
      assert(acks == 1 && packets.size() == 1 && packets[0].size() == 36);
      assert(packets[0][0] == 240 && packets[0][1] == 29 &&
             packets[0][35] == 247);
      for (unsigned i = 0; i < 33; ++i)
        assert(packets[0][i + 2] == i);
    } else
      assert(packets.empty() && acks == 0);
    std::cout << "case " << cases << " calls " << expected.size() << " state ";
    for (auto b : actualState)
      std::cout << std::hex << unsigned(b / 16) << unsigned(b % 16);
    std::cout << " packets ";
    for (auto &v : actualPackets) {
      for (auto b : v)
        std::cout << std::hex << unsigned(b / 16) << unsigned(b % 16);
      std::cout << ",";
    }
    std::cout << std::dec << "\n";
    if (kind == 2) {
      p.size = 39;
      bool caught = false;
      try {
        handler.setPropertyDeferred(p);
      } catch (const std::invalid_argument &) {
        caught = true;
      }
      assert(caught);
      p.size = 40;
      hs.deferredRate = nullptr;
      caught = false;
      try {
        handler.setPropertyDeferred(p);
      } catch (const std::invalid_argument &) {
        caught = true;
      }
      assert(caught);
    }
    if (kind == 3) {
      hs.deferredRoutes = nullptr;
      bool caught = false;
      try {
        handler.setPropertyDeferred(p);
      } catch (const std::invalid_argument &) {
        caught = true;
      }
      assert(caught);
    }
    ++cases;
  }
  std::cout
      << "PASS " << cases
      << " actual Handler dispatch/provider cases; zero device operations\n";
}
