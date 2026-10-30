#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dice/codec.hpp"
#include "presonus/dsp/audio_hal.hpp"
#include "presonus/noaa/card.hpp"
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Presonus;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static CardState *state;
static TCard *card;
static std::string trace;
static unsigned ack, clocks, posts, responses, resets, dacs, created;
static std::int64_t tick;
static bool realProvider, exactPackets = true;
static bool dacMutation;
static std::uint32_t dacValue;
static std::vector<std::pair<unsigned, std::uint32_t>> response20, response40;
static std::vector<unsigned> waitStack;
struct Packet {
  unsigned length;
  std::string bytes;
  std::int64_t timestamp;
};
static std::vector<Packet> expectedPackets;
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
static auto unhex(const std::string &s) {
  assert(s.size() % 2 == 0);
  std::vector<unsigned char> r;
  for (std::size_t i = 0; i < s.size(); i += 2)
    r.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return r;
}
static const unsigned offsets[] = {0x14, 0x18, 0x1c, 0x20, 0x24, 0x28,
                                   0x2c, 0x30, 0x34, 0x38, 0x3c, 0x40,
                                   0x44, 0x4c, 0x50, 0x54, 0x58};
static std::uint32_t &field(unsigned offset) {
  switch (offset) {
  case 0x14:
    return state->observedWord14;
  case 0x18:
    return state->observedWord18;
  case 0x1c:
    return state->observedWord1c;
  case 0x20:
    return state->observedWord20;
  case 0x24:
    return state->observedWord24;
  case 0x28:
    return state->observedWord28;
  case 0x2c:
    assert(state->expectedSerial);
    return *state->expectedSerial;
  case 0x30:
    return state->observedWord30;
  case 0x34:
    return state->observedWord34;
  case 0x38:
    return state->observedWord38;
  case 0x3c:
    return state->observedWord3c;
  case 0x40:
    return state->observedWord40;
  case 0x44:
    return state->observedWord44;
  case 0x4c:
    return state->observedWord4c;
  case 0x50:
    return state->observedWord50;
  case 0x54:
    return state->observedWord54;
  case 0x58:
    return state->observedWord58;
  default:
    std::abort();
  }
}
static void appendWord(std::vector<unsigned char> &v, std::uint32_t x) {
  for (unsigned i = 0; i < 4; ++i)
    v.push_back(x >> (8 * i));
}
static std::string snapshot() {
  std::vector<unsigned char> v;
  for (auto offset : offsets)
    appendWord(v, field(offset));
  v.push_back(card->portableState().command);
  v.push_back(card->portableState().status);
  appendWord(v, card->portableState().infoWords[0]);
  v.push_back(state->observedByte48);
  v.insert(v.end(), state->commandShadow.begin(), state->commandShadow.end());
  return hex(v.data(), v.size());
}
static void load(const std::string &s) {
  auto v = unhex(s);
  assert(v.size() == 83);
  state->expectedSerial = 0;
  unsigned at = 0;
  for (auto offset : offsets) {
    std::uint32_t x = 0;
    for (unsigned i = 0; i < 4; ++i)
      x |= std::uint32_t(v[at++]) << (8 * i);
    field(offset) = x;
  }
  card->portableState().command = v[at++];
  card->portableState().status = v[at++];
  std::uint32_t x = 0;
  for (unsigned i = 0; i < 4; ++i)
    x |= std::uint32_t(v[at++]) << (8 * i);
  card->portableState().infoWords[0] = x;
  state->observedByte48 = v[at++];
  std::copy(v.begin() + at, v.end(), state->commandShadow.begin());
}
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  assert(clocks < 32);
  return tick + std::int64_t(clocks++) * 1000003;
}
} // namespace presonus::dice
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  trace += "D:" + hex(format);
  va_list ap;
  va_start(ap, format);
  for (auto *p = format; *p; ++p) {
    if (*p != '%')
      continue;
    ++p;
    if (*p == '%')
      continue;
    while (*p && std::strchr("#0- +'123456789.", *p))
      ++p;
    assert(*p);
    if (*p == 's') {
      auto *s = va_arg(ap, const char *);
      trace += ":" + (s ? "s" + hex(s) : "NULL");
    } else if (*p == 'd' || *p == 'i')
      trace += ":" + std::to_string(va_arg(ap, int));
    else {
      assert(*p == 'u' || *p == 'x' || *p == 'X');
      trace += ":" + std::to_string(va_arg(ap, unsigned));
    }
  }
  va_end(ap);
  trace += ';';
}
struct Pins final : presonus::surface_panel_port::InputPinIO {
  unsigned opens = 0, closes = 0, gets = 0;
  std::FILE *open(const char *, const char *) override {
    return reinterpret_cast<std::FILE *>(
        std::uintptr_t(0x10000 + 256 * ++opens));
  }
  int printPin(std::FILE *, const char *, int pin) override {
    assert(pin == 34 || pin == 137);
    return 1;
  }
  int close(std::FILE *) override {
    ++closes;
    return 0;
  }
  void formatPath(char *out, std::size_t n, const char *f, int pin) override {
    std::snprintf(out, n, f, pin);
  }
  std::size_t write(const void *p, std::size_t size, std::size_t n,
                    std::FILE *) override {
    assert(size == 1 && n == 2 && std::memcmp(p, "in", 2) == 0);
    return 2;
  }
  int buffering(std::FILE *, char *, int, std::size_t) override { return 0; }
  void rewind(std::FILE *) override {}
  int flush(std::FILE *) override { return 0; }
  int get(std::FILE *) override {
    ++gets;
    return '0';
  }
  void notify(Panel::PinStateObserver *, int, int) override { std::abort(); }
  void log(const char *) override { std::abort(); }
};
struct IO final : SpiServiceIO {
  unsigned transfers = 0, closes = 0, opens = 0;
  int open(const char *, int) override {
    assert(realProvider);
    ++opens;
    return 71;
  }
  int maxSpeed(int fd, std::uint32_t value) override {
    assert(realProvider && fd == 71 && value == 20000000);
    return 0;
  }
  int close(int fd) override {
    assert(fd == 71);
    ++closes;
    return 0;
  }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override {
    assert(realProvider);
    return 4500000;
  }
  int transfer(int fd, const SpiTransfer &t) override {
    assert(realProvider && (fd == 71 || fd == -1));
    ++transfers;
    assert(t.length > 0 && t.length <= 255);
    std::fill_n(t.rx, t.length, static_cast<unsigned char>(0xf8));
    return t.length;
  }
  void diagnostic(bool out, const char *text, int, bool arg) override {
    assert(realProvider && !out && !arg &&
           std::strcmp(text, "TCard open") == 0);
  }
};
static Pins &pins() {
  static Pins p;
  return p;
}
static IO &io() {
  static IO p;
  return p;
}
extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *p) {
  assert(p == static_cast<Core::Portable::Deletable *>(
                  SpiServiceAccess::singleton()));
  ++created;
  trace += "C;";
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(p);
}
extern "C" void __real__ZN8Presonus4NOAA8TCardSPI6onIdleEb(TCardSPI *, bool);
extern "C" void __wrap__ZN8Presonus4NOAA8TCardSPI6onIdleEb(TCardSPI *self,
                                                           bool value) {
  assert(self == SpiServiceAccess::singleton() && value);
  trace += "I;";
  if (realProvider)
    __real__ZN8Presonus4NOAA8TCardSPI6onIdleEb(self, value);
}
extern "C" unsigned char
__real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *, long long);
extern "C" unsigned char
__wrap__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(SysexReceiver *self,
                                                  long long timeout) {
  assert(self == card && timeout == 500);
  trace += "W:" + std::to_string(ack) + ";";
  if (realProvider) {
    waitStack.push_back(0);
    auto value =
        __real__ZN8Presonus4NOAA13SysexReceiver7waitAckEx(self, timeout);
    waitStack.pop_back();
    return value;
  }
  self->portableState().command = ack;
  return ack;
}
extern "C" bool __real__ZN8Presonus4NOAA13SysexReceiver15waitResponseSetERjx(
    SysexReceiver *, unsigned int &, long long);
extern "C" bool __wrap__ZN8Presonus4NOAA13SysexReceiver15waitResponseSetERjx(
    SysexReceiver *self, unsigned int &value, long long timeout) {
  assert(self == card);
  unsigned offset = &value == &state->observedWord20 ? 0x20 : 0x40;
  assert(&value == &field(offset) && timeout == (offset == 0x20 ? 6000 : 3000));
  ++responses;
  trace += "R:" + std::to_string(offset) + ":" + std::to_string(timeout) + ":" +
           snapshot() + ";";
  if (realProvider) {
    waitStack.push_back(offset);
    bool result = __real__ZN8Presonus4NOAA13SysexReceiver15waitResponseSetERjx(
        self, value, timeout);
    waitStack.pop_back();
    return result;
  }
  if (value == 0)
    for (auto update : offset == 0x20 ? response20 : response40)
      field(update.first) = update.second;
  return value != 0;
}
static unsigned lastCommand;
struct Fixture final : TCard {
  using TCard::TCard;
  bool updateFirmware(UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  void post(SysexPacket &p) override {
    assert(clocks >= 2);
    if (exactPackets) {
      assert(posts < expectedPackets.size());
      auto &e = expectedPackets[posts];
      assert(p.length == e.length && hex(p.bytes.data(), p.length) == e.bytes &&
             p.portableMetadata().constructedQuotient == e.timestamp);
    }
    assert(
        (p.portableMetadata().headerWords == std::array<std::uint32_t, 2>{}));
    assert(
        (p.portableMetadata().trailingWords == std::array<std::uint32_t, 4>{}));
    for (unsigned i = p.length; i < 255; ++i)
      assert(p.bytes[i] == 0x45);
    ++posts;
    lastCommand = p.bytes[1];
    trace += "P;";
    if (realProvider)
      SysexReceiver::post(p);
    else {
      portableState().command = 0;
      portableState().status = 0;
      portableState().infoWords[0] = 0;
    }
  }
};
struct Prefix {
  virtual ~Prefix() = default;
};
struct HAL final : Prefix, Dsp::IAudioHAL {
  void resetBoard(int mode, int board) override {
    assert(mode == 2 && board == 0);
    ++resets;
    trace += "H:reset:" + snapshot() + ";";
  }
  void enableDACs(bool enabled, bool clock, int board) override {
    assert(board == 2);
    ++dacs;
    trace += "H:dacs:" + std::to_string(enabled) + ":" + std::to_string(clock) +
             ":" + snapshot() + ";";
    if (dacMutation)
      state->observedWord40 = dacValue;
  }
  void enableAMP(bool) override { std::abort(); }
  void suspendControlSurfaces(bool) override { std::abort(); }
};
struct Pump final : presonus::dice::IdlePump {
  unsigned calls = 0, received = 0;
  void onIdle(bool force) override {
    assert(realProvider && !force && !waitStack.empty());
    ++calls;
    SysexPacket p;
    p.length = 4;
    p.bytes[0] = 0xf0;
    p.bytes[3] = 0xf7;
    if (waitStack.back() == 0) {
      p.bytes[1] = lastCommand;
      p.bytes[2] = 1;
    } else if (waitStack.back() == 0x20) {
      p.length = 34;
      p.bytes[1] = 1;
      p.bytes[2] = 1;
      for (unsigned offset : {3u, 8u, 13u})
        pack32(0x12340000, p.bytes.data() + offset);
      pack32(123, p.bytes.data() + 18);
      pack32(456, p.bytes.data() + 23);
      pack32(0, p.bytes.data() + 28);
      p.bytes[33] = 23;
    } else {
      assert(waitStack.back() == 0x40);
      p.bytes[1] = 19;
      p.bytes[2] = 2;
    }
    ++received;
    static_cast<ISysexReceiver *>(card)->receive(p);
  }
};
static void afterCleanup() {
  assert(SpiServiceAccess::singleton() == nullptr && created == 1 &&
         pins().opens == 6 && pins().closes == 6 && io().closes == 1);
  std::cout << "{\"passed\":true,\"actual_ccl_registry_cleanup\":true,\"typed_"
               "provider_lifetimes\":true,\"physical_operations\":0}\n";
}
int main(int argc, char **argv) {
  assert(argc == 2);
  auto &pinProvider = pins();
  auto &spiProvider = io();
  assert(presonus::surface_panel_port::setInputPinConstructionIO(
             &pinProvider) == nullptr);
  assert(setSpiServiceConstructionIO(&spiProvider) == nullptr);
  assert(SpiServiceAccess::singleton() == nullptr);
  assert(std::atexit(afterCleanup) == 0);
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  ResourceLibrary resources;
  CardState storage{};
  state = &storage;
  state->resources = &resources;
  HAL hal;
  auto *typed = static_cast<Dsp::IAudioHAL *>(&hal);
  assert(static_cast<void *>(typed) != static_cast<void *>(&hal));
  Fixture object(cardSetupTag, *state, response, spiProvider);
  card = &object;
  std::ifstream input(argv[1]);
  std::string kind;
  unsigned cases = 0, excluded = 0;
  SysexPacket packet;
  while (input >> kind) {
    unsigned argument, present, mutate, domain, result, mask20, mask40, n;
    std::uint32_t v20, v44, v18, v3c, v40;
    std::string initial, output, packetHex, expectedTrace;
    input >> argument >> present >> mutate >> dacValue >> mask20 >> v20 >>
        v44 >> v18 >> v3c >> mask40 >> v40 >> tick >> ack >> initial >>
        output >> domain >> result >> packetHex >> n;
    expectedPackets.clear();
    for (unsigned i = 0; i < n; ++i) {
      Packet p;
      input >> p.length >> p.bytes >> p.timestamp;
      expectedPackets.push_back(p);
    }
    input >> expectedTrace;
    load(initial);
    state->opaque5c.value =
        present ? static_cast<const void *>(typed) : nullptr;
    state->audioHal = typed;
    state->opaque2c.value =
        reinterpret_cast<const void *>(std::uintptr_t(0xdeadbeef));
    auto opaqueBefore = state->opaque2c.value;
    dacMutation = mutate;
    response20.clear();
    response40.clear();
    if (mask20)
      response20 = {{0x20, v20}, {0x44, v44}, {0x18, v18}, {0x3c, v3c}};
    if (mask40)
      response40 = {{0x40, v40}};
    clocks = posts = 0;
    trace.clear();
    bool threw = false;
    try {
      if (kind == "R") {
        packet.length = argument;
        auto b = unhex(packetHex);
        assert(b.size() == 256);
        std::copy(b.begin(), b.end(), packet.bytes.begin());
        card->receive(packet);
      } else {
        assert(kind == "S");
        assert(card->start(argument != 0) == result);
      }
    } catch (const std::logic_error &) {
      assert(!domain);
      threw = true;
      ++excluded;
    }
    if (!domain) {
      assert(threw);
      auto suffix = std::string("F:0:4;");
      assert(expectedTrace.size() >= suffix.size() &&
             expectedTrace.compare(expectedTrace.size() - suffix.size(),
                                   suffix.size(), suffix) == 0);
      expectedTrace.resize(expectedTrace.size() - suffix.size());
    } else
      assert(!threw);
    if (snapshot() != output ||
        trace != (expectedTrace == "-" ? "" : expectedTrace) ||
        state->opaque2c.value != opaqueBefore) {
      std::cerr << "Mismatch case " << cases << " " << kind << "\nACTUAL "
                << trace << "\nEXPECTED " << expectedTrace << "\nSTATE "
                << snapshot() << "\nWANT " << output << '\n';
      return 1;
    }
    assert(posts == expectedPackets.size());
    ++cases;
  }
  assert(input.eof() && cases == 65920 && excluded == 80);
  // Native-only branch-local preconditions, not original-equivalence claims.
  exactPackets = false;
  state->expectedSerial.reset();
  packet.length = 2;
  packet.bytes[1] = 2;
  state->opaque5c.value = nullptr;
  card->receive(packet);
  unsigned guards = 0;
  packet.bytes.fill(0);
  packet.length = 34;
  packet.bytes[1] = 1;
  try {
    card->receive(packet);
  } catch (const std::logic_error &) {
    ++guards;
  }
  assert(guards == 1 && !state->expectedSerial);
  state->expectedSerial = 0;
  state->audioHal = nullptr;
  state->opaque5c.value = typed;
  packet.length = 3;
  packet.bytes[1] = 18;
  state->observedWord18 = 0;
  card->receive(packet);
  state->observedWord18 = 1;
  try {
    card->receive(packet);
  } catch (const std::logic_error &) {
    ++guards;
  }
  packet.bytes[1] = 19;
  try {
    card->receive(packet);
  } catch (const std::logic_error &) {
    ++guards;
  }
  state->audioHal = typed;
  state->opaque5c.value = &storage;
  try {
    card->receive(packet);
  } catch (const std::logic_error &) {
    ++guards;
  }
  state->opaque5c.value = nullptr;
  clocks = 0;
  tick = 0;
  card->receive(packet);
  assert(guards == 4);
  // End-to-end actual CCL/SPI source path, with HAL reset/DAC effects captured.
  realProvider = true;
  dacMutation = false;
  state->audioHal = typed;
  state->expectedSerial = 123;
  state->observedWord18 = 0;
  state->observedWord44 = 0;
  state->observedWord40 = 0;
  state->resources = &resources;
  NOAASetupProperty prop(
      "offline-spi", {typed}, rm13731GambitRouterSlots(), 23,
      {reinterpret_cast<const void *>(std::uintptr_t(0xdeadbeef))});
  assert(card->open(prop) == 1);
  auto &spi = TCardSPI::instance();
  const int count = SpiServiceAccess::state(spi).receivers.count();
  spi.registerReceiver(card);
  clocks = posts = 0;
  tick = 0;
  ack = 85;
  assert(card->start(true));
  assert(state->observedWord18 == 1 && state->observedWord40 == 1 &&
         state->observedWord44 == 1 && state->observedWord34 == 123 &&
         state->observedWord1c == 1 && posts >= 4 && pump.received >= 5 &&
         io().transfers >= posts);
  spi.unRegisterReceiver(card);
  assert(SpiServiceAccess::state(spi).receivers.count() == count);
  realProvider = false;
  std::cout << "{\"passed\":true,\"original_cases\":" << cases
            << ",\"original_null_start_exclusions\":" << excluded
            << ",\"native_guard_cases\":4,\"physical_capacity\":256,\"real_spi_"
               "ccl_hal_provider\":true,\"original_hal_offset_not_used\":true,"
               "\"physical_operations\":0}\n";
}
