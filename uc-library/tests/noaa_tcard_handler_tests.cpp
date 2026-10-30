#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/status_property.hpp"
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static unsigned clocks, statusCalls, macCalls, ackCalls, generated, serial;
static unsigned char ack;
static std::vector<SysexPacket> packets;
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  return -1000001 + std::int64_t(clocks++) * 1000003;
}
} // namespace presonus::dice
extern "C" void
__wrap__ZN8Presonus4NOAA5TCard17getStatusPropertyERNS0_18NOAAStatusPropertyE(
    TCard *, NOAAStatusProperty &p) {
  ++statusCalls;
  p.payload.fill(0x71);
}
extern "C" unsigned int
__wrap__ZN8Presonus4NOAA5TCard20generateAlternateMacEj(TCard *,
                                                       unsigned int value) {
  assert(value == serial);
  ++macCalls;
  return generated;
}
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *,
                                                  long long timeout) {
  assert(timeout == 500);
  ++ackCalls;
  return ack;
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
struct Card final : TCard {
  Card(CardState &s, Response &r, IO &i) : TCard(cardSetupTag, s, r, i) {}
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
};
struct Handler final : TCardHandler {
  Handler(CardHandlerState &s, Response &r)
      : TCardHandler(cardHandlerSetupTag, s, r) {}
  void setProperty(const Core::Property &) override { std::abort(); }
  void release() override { std::abort(); }
  int threadEntry() override { std::abort(); }
  void post(SysexPacket &p) override { packets.push_back(p); }
};
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
  Response response;
  IO io;
  CardState cardState{};
  Card card(cardState, response, io);
  CardHandlerState state{card};
  Handler handler(state, response);
  while (std::getline(file, line)) {
    std::istringstream in(line);
    std::string method;
    in >> method;
    clocks = statusCalls = macCalls = ackCalls = 0;
    packets.clear();
    if (method == "accepts") {
      unsigned n, b, expected;
      in >> n >> b >> expected;
      SysexPacket p;
      p.length = n;
      p.bytes[1] = b;
      assert(handler.accepts(p) == bool(expected));
    } else if (method == "getProperty") {
      unsigned tag, calls;
      in >> tag >> calls;
      NOAAStatusProperty p(std::array<unsigned char, 52>{});
      p.type = tag;
      p.payload.fill(0x39);
      state.statusProperty = &p;
      Core::IPropertyHandler &base = handler;
      base.getProperty(p);
      assert(statusCalls == calls);
      for (auto b : p.payload)
        assert(b == (calls ? 0x71 : 0x39));
    } else if (method == "getAlternateMac") {
      unsigned long long expected;
      in >> serial >> generated >> expected;
      state.expectedSerial = serial;
      assert(handler.getAlternateMac() == expected);
      assert(macCalls == 1);
    } else {
      assert(method == "sendGEQBulkProperty");
      std::string payloadHex, packetHex;
      unsigned ackValue, expectedClocks;
      long long timestamp;
      in >> payloadHex >> ackValue >> expectedClocks >> packetHex >> timestamp;
      auto payload = unhex(payloadHex);
      std::array<unsigned char, 33> bytes;
      std::copy(payload.begin(), payload.end(), bytes.begin());
      Core::Property p(0, 8);
      state.geqProperty = &p;
      state.geqPayload = &bytes;
      ack = ackValue;
      assert(handler.sendGEQBulkProperty(p) == 0);
      assert(clocks == expectedClocks && ackCalls == 1 && packets.size() == 1);
      auto expected = unhex(packetHex);
      assert(packets[0].length == expected.size());
      assert(std::equal(expected.begin(), expected.end(),
                        packets[0].bytes.begin()));
      assert(packets[0].portableMetadata().constructedQuotient == timestamp);
      state.geqPayload = nullptr;
    }
    ++cases;
  }
  unsigned guards = 0;
  state.expectedSerial.reset();
  try {
    handler.getAlternateMac();
    assert(false);
  } catch (const std::invalid_argument &) {
    ++guards;
  }
  state.statusProperty = nullptr;
  Core::Property unboundStatus(NOAAStatusProperty::kID, sizeof(Core::Property));
  try {
    handler.getProperty(unboundStatus);
    assert(false);
  } catch (const std::invalid_argument &) {
    ++guards;
  }
  Core::Property unboundGeq(0, sizeof(Core::Property));
  state.geqProperty = nullptr;
  state.geqPayload = nullptr;
  try {
    handler.sendGEQBulkProperty(unboundGeq);
    assert(false);
  } catch (const std::invalid_argument &) {
    ++guards;
  }
  assert(guards == 3);
  std::cout << "{\"passed\":true,\"handler_cases\":" << cases
            << ",\"actual_device_operations\":0}\n";
}
