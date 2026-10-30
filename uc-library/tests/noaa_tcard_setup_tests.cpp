#include "presonus/noaa/card.hpp"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <type_traits>
#include <vector>
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::vector<std::string> events;
static std::uint32_t rawResult;
static bool actualOpen;
static CardState *currentState;
static CardState expectedBefore;
static const NOAASetupProperty *currentProperty;
static unsigned sleeps, spiInstances, providerOpens;
struct Pins final : presonus::surface_panel_port::InputPinIO {
  unsigned opens = 0, closes = 0;
  std::FILE *open(const char *, const char *) override {
    ++opens;
    return reinterpret_cast<std::FILE *>(std::uintptr_t(opens * 256 + 0x10000));
  }
  int printPin(std::FILE *, const char *format, int pin) override {
    assert(std::strcmp(format, "%d") == 0 && (pin == 34 || pin == 137));
    return 1;
  }
  int close(std::FILE *) override {
    ++closes;
    return 0;
  }
  void formatPath(char *out, std::size_t n, const char *fmt, int pin) override {
    std::snprintf(out, n, fmt, pin);
  }
  std::size_t write(const void *p, std::size_t n, std::size_t count,
                    std::FILE *) override {
    assert(n == 1 && count == 2 && std::memcmp(p, "in", 2) == 0);
    return 2;
  }
  int buffering(std::FILE *, char *, int, std::size_t) override { return 0; }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
  void log(const char *) override { std::abort(); }
};
struct IO final : SpiServiceIO {
  unsigned closes = 0;
  int mode = 0;
  int open(const char *path, int) override {
    assert(path == currentProperty->spiPath);
    ++providerOpens;
    events.emplace_back("provider_open");
    return mode == 1 ? -37 : 71;
  }
  int maxSpeed(int fd, std::uint32_t speed) override {
    assert(fd == 71 && speed == 20000000);
    events.emplace_back("provider_speed");
    return mode == 2 ? -1 : 0;
  }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int fd) override {
    assert(fd == 71 || fd == -37);
    ++closes;
    return 0;
  }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool out, const char *text, int value, bool arg) override {
    if (std::strcmp(text, "TCard open") == 0) {
      assert(!out && !arg && currentState);
      assert(currentState->opaque5c.value == expectedBefore.opaque5c.value &&
             currentState->observedWord30 == expectedBefore.observedWord30 &&
             currentState->observedWord40 == expectedBefore.observedWord40 &&
             currentState->opaque2c.value == expectedBefore.opaque2c.value);
      events.emplace_back("log");
    } else {
      assert(out);
      if (mode == 1)
        assert(arg && value == -37 &&
               std::strcmp(text, "error opening NOAA device %d\n") == 0);
      else
        assert(mode == 2 && !arg &&
               std::strcmp(text, "error: SPI max_speed_hz") == 0);
      events.emplace_back("provider_error");
    }
  }
};
static Pins &pins() {
  static Pins value;
  return value;
}
static IO &io() {
  static IO value;
  return value;
}
extern "C" int __real__ZN8Presonus4NOAA8TCardSPI4openEPKc(TCardSPI *,
                                                          const char *);
extern "C" int __wrap__ZN8Presonus4NOAA8TCardSPI4openEPKc(TCardSPI *spi,
                                                          const char *path) {
  assert(spi == SpiServiceAccess::singleton() &&
         path == currentProperty->spiPath);
  assert(currentState->opaque5c.value == currentProperty->opaque0c.value &&
         currentState->observedWord30 == currentProperty->observedWord1c &&
         currentState->observedWord40 == 0 &&
         currentState->opaque2c.value == currentProperty->opaque20.value);
  events.emplace_back("spi_open");
  if (actualOpen)
    return __real__ZN8Presonus4NOAA8TCardSPI4openEPKc(spi, path);
  std::int32_t value;
  std::memcpy(&value, &rawResult, 4);
  return value;
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned ms) {
  assert(ms == 1);
  ++sleeps;
  events.emplace_back("sleep_1");
}
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool) override { std::abort(); }
};
struct Fixture final : TCard {
  using TCard::TCard;
  void receive(const SysexPacket &) override { std::abort(); }
  bool isFirmwareCompatible(int) override { std::abort(); }
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
};
static_assert(std::is_abstract_v<TCard>);
static void afterCleanup() {
  assert(SpiServiceAccess::singleton() == nullptr);
  assert(pins().opens == pins().closes);
  assert(io().closes == 3); // includes retained SPI open-failure descriptor -37
  std::cout << "{\"passed\":true,\"actual_ccl_registry_cleanup\":true,"
               "\"provider_lifetimes_valid\":true,\"pin_closes\":"
            << pins().closes << ",\"physical_operations\":0}\n";
}
int main(int argc, char **argv) {
  assert(argc == 2);
  auto &p = pins();
  auto &provider = io();
  auto *previousPins =
      presonus::surface_panel_port::setInputPinConstructionIO(&p);
  auto *previousIO = setSpiServiceConstructionIO(&provider);
  assert(previousPins == nullptr && previousIO == nullptr &&
         SpiServiceAccess::singleton() == nullptr);
  assert(std::atexit(afterCleanup) ==
         0); // registered before actual CCL singleton registry
  Pump pump;
  presonus::dice::CclResponseServices response(pump);
  CardState state{};
  currentState = &state;
  Fixture card(cardSetupTag, state, response, provider);
  std::ifstream input(argv[1]);
  std::string kind;
  unsigned cases = 0;
  SysexPacket packet;
  while (input >> kind) {
    if (kind == "A") {
      unsigned length, command, result;
      input >> length >> command >> result;
      packet.length = length;
      packet.bytes[1] = command;
      assert(card.accepts(packet) == result);
    } else if (kind == "M") {
      std::uint32_t value, result;
      input >> value >> result;
      state.observedWord44 = value;
      Presonus::IDeviceDFU *base = &card;
      assert(base->isMounted() == result);
    } else if (kind == "D") {
      unsigned value, result;
      input >> value >> result;
      state.observedByte48 = value;
      assert(card.isDesktopConnected() == result);
    } else if (kind == "S") {
      std::uint32_t value;
      std::string expected;
      input >> value >> expected;
      state.observedWord14 = value;
      auto *s = card.getCardCString();
      assert(expected == "NULL" ? s == nullptr : s && expected == s);
    } else if (kind == "O") {
      unsigned existing;
      std::uint32_t a, b, c;
      input >> existing >> rawResult >> a >> b >> c;
      if (!existing) {
        SpiServiceAccess::singleton(nullptr);
        ++spiInstances;
      } else
        assert(SpiServiceAccess::singleton());
      auto &slots = rm13731GambitRouterSlots();
      NOAASetupProperty prop(
          "offline-spi", {reinterpret_cast<const void *>(std::uintptr_t(a))},
          slots, b, {reinterpret_cast<const void *>(std::uintptr_t(c))});
      currentProperty = &prop;
      expectedBefore = state;
      events.clear();
      auto result = card.open(prop);
      std::uint32_t returned;
      std::memcpy(&returned, &result, 4);
      assert(returned == rawResult);
      assert(
          (events == std::vector<std::string>{"log", "spi_open", "sleep_1"}));
    } else
      std::abort();
    ++cases;
  }
  assert(input.eof() && cases == 65832);
  // Actual SPI open provider regressions: failure, speed failure and success.
  actualOpen = true;
  for (int mode = 0; mode < 3; ++mode) {
    SpiServiceAccess::singleton(nullptr);
    ++spiInstances;
    provider.mode = mode;
    NOAASetupProperty prop("offline-provider", {nullptr},
                           rm13731GambitRouterSlots(), 27, {nullptr});
    currentProperty = &prop;
    expectedBefore = state;
    events.clear();
    int result = card.open(prop);
    assert(result == (mode == 0 ? 1 : 0));
    assert(events.front() == "log" && events[1] == "spi_open" &&
           events[2] == "provider_open" && events.back() == "sleep_1");
    if (mode == 1)
      assert(events[3] == "provider_error");
    else {
      assert(events[3] == "provider_speed");
      if (mode == 2)
        assert(events[4] == "provider_error");
    }
  }
  assert(providerOpens == 3 && spiInstances == 13 && sleeps == 23 &&
         p.opens == 78 && p.closes == 52);
  // Providers remain alive through actual CCL registry teardown. No manual
  // deletion of registered objects; registry destructor deletes all13
  // instances.
  std::cout
      << "{\"passed\":true,\"original_cases\":" << cases
      << ",\"real_spi_provider_cases\":3,\"actual_ccl_singleton_instances\":"
      << spiInstances
      << ",\"raw_desktop_bytes\":256,\"physical_operations\":0}\n";
}
