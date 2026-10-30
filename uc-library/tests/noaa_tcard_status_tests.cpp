#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/noaa/card.hpp"
#include "presonus/noaa/status_property.hpp"
#include <cassert>
#include <cstdarg>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
using namespace Presonus;
using namespace Presonus::NOAA;
using namespace presonus::noaa;
static std::string trace;
static bool inVersion;
static std::string hex(const unsigned char *p, std::size_t n) {
  static const char *digits = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    s += digits[p[i] >> 4];
    s += digits[p[i] & 15];
  }
  return s;
}
static std::string hex(const char *s) {
  return hex(reinterpret_cast<const unsigned char *>(s), std::strlen(s));
}
static std::vector<unsigned char> unhex(const std::string &s) {
  assert(s.size() % 2 == 0);
  std::vector<unsigned char> p;
  for (std::size_t i = 0; i < s.size(); i += 2)
    p.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return p;
}
extern "C" FirmwareBundle *
__real__ZN8Presonus15ResourceLibrary3getEPKc(ResourceLibrary *, const char *);
extern "C" FirmwareBundle *
__wrap__ZN8Presonus15ResourceLibrary3getEPKc(ResourceLibrary *lib,
                                             const char *name) {
  if (!inVersion)
    trace += "B:" + hex(name) + ";";
  return __real__ZN8Presonus15ResourceLibrary3getEPKc(lib, name);
}
extern "C" unsigned
__real__ZN8Presonus15ResourceLibrary18getRequiredVersionEPKc(ResourceLibrary *,
                                                             const char *);
extern "C" unsigned
__wrap__ZN8Presonus15ResourceLibrary18getRequiredVersionEPKc(
    ResourceLibrary *lib, const char *name) {
  trace += "V:" + hex(name) + ";";
  assert(!inVersion);
  inVersion = true;
  auto value =
      __real__ZN8Presonus15ResourceLibrary18getRequiredVersionEPKc(lib, name);
  inVersion = false;
  return value;
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  va_list args;
  va_start(args, format);
  auto expected = va_arg(args, unsigned);
  auto found = va_arg(args, unsigned);
  va_end(args);
  trace += "D:" + hex(format) + ":" + std::to_string(expected) + ":" +
           std::to_string(found) + ";";
}
static NOAAStatusProperty *observedProperty;
static std::vector<std::string> callbackImages;
static std::vector<int> callbackModes;
static std::string image(const NOAAStatusProperty &property) {
  std::array<unsigned char, 60> b;
  std::memcpy(b.data(), &property.type, 4);
  std::memcpy(b.data() + 4, &property.size, 4);
  std::memcpy(b.data() + 8, property.payload.data(), 52);
  return hex(b.data(), b.size());
}
struct Fixture final : TCard {
  using TCard::TCard;
  void receive(const SysexPacket &) override { std::abort(); }
  bool updateFirmware(UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
  bool isMounted() override {
    if (observedProperty) {
      callbackModes.push_back(-1);
      callbackImages.push_back(image(*observedProperty));
    }
    return TCard::isMounted();
  }
  bool isFirmwareCompatible(int mode) override {
    if (observedProperty) {
      callbackModes.push_back(mode);
      callbackImages.push_back(image(*observedProperty));
    }
    return TCard::isFirmwareCompatible(mode);
  }
};
struct Pump final : presonus::dice::IdlePump {
  void onIdle(bool) override { std::abort(); }
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
  std::string kind;
  unsigned cases = 0;
  while (input >> kind) {
    if (kind == "L") {
      unsigned index;
      input >> index;
      libs[index] = std::make_unique<ResourceLibrary>();
      for (auto *name : names) {
        unsigned present, value;
        input >> present >> value;
        if (present) {
          libs[index]->addFirmware(name, value, &dummy, 1, false);
          libs[index]->addFirmware(name, value ^ 1, &dummy, 1, false);
        }
      }
      continue;
    }
    std::uint32_t type;
    unsigned lib;
    input >> type >> lib;
    assert(lib < 5 && libs[lib]);
    state.observedWord14 = type;
    state.resources = libs[lib].get();
    if (kind == "C") {
      long long mode;
      unsigned expected;
      std::string expectedTrace;
      input >> mode >> state.observedWord20 >> state.observedWord28 >>
          expected >> expectedTrace;
      trace.clear();
      auto result = card.isFirmwareCompatible(static_cast<int>(mode));
      assert(result == expected &&
             trace == (expectedTrace == "-" ? "" : expectedTrace));
    } else if (kind == "A" || kind == "F") {
      std::string expected, expectedTrace;
      input >> expected >> expectedTrace;
      auto *pointer =
          expected == "NULL" ? nullptr : state.resources->get(expected.c_str());
      trace.clear();
      auto *actual = kind == "A" ? card.getArmFirmwareBundle()
                                 : card.getFpgaFirmwareBundle();
      assert(actual == pointer && trace == expectedTrace);
    } else if (kind == "S") {
      input >> state.observedWord18 >> state.observedWord1c >>
          state.observedWord20 >> state.observedWord24 >>
          state.observedWord28 >> state.observedWord34 >>
          state.observedWord38 >> state.observedWord3c >>
          state.observedWord40 >> state.observedWord44 >>
          state.observedWord4c >> state.observedWord50 >>
          state.observedWord54 >> state.observedWord58;
      unsigned desktop;
      std::string initial, expected, c0, c1, c2, expectedTrace;
      input >> desktop >> initial >> expected >> c0 >> c1 >> c2 >>
          expectedTrace;
      state.observedByte48 = desktop;
      auto bytes = unhex(initial);
      assert(bytes.size() == 60);
      std::array<unsigned char, 52> seed;
      std::memcpy(seed.data(), bytes.data() + 8, 52);
      NOAAStatusProperty property(seed);
      std::memcpy(&property.type, bytes.data(), 4);
      std::memcpy(&property.size, bytes.data() + 4, 4);
      observedProperty = &property;
      callbackModes.clear();
      callbackImages.clear();
      trace.clear();
      card.getStatusProperty(property);
      observedProperty = nullptr;
      assert(image(property) == expected);
      assert((callbackModes == std::vector<int>{-1, 2, 3}));
      assert((callbackImages == std::vector<std::string>{c0, c1, c2}));
      assert(trace == (expectedTrace == "-" ? "" : expectedTrace));
    } else
      std::abort();
    ++cases;
  }
  assert(input.eof() && cases == 2560);
  state.resources = nullptr;
  unsigned guards = 0;
  for (int which = 0; which < 3; ++which) {
    try {
      if (which == 0)
        card.getArmFirmwareBundle();
      else if (which == 1)
        card.getFpgaFirmwareBundle();
      else
        card.isFirmwareCompatible(2);
    } catch (const std::logic_error &) {
      ++guards;
    }
  }
  assert(guards == 3);
  std::cout << "{\"passed\":true,\"original_cases\":" << cases
            << ",\"real_resource_libraries\":5,\"duplicate_first_match\":true,"
               "\"status_callback_order_and_snapshots\":true,\"native_property_"
               "size\":"
            << sizeof(NOAAStatusProperty)
            << ",\"missing_binding_guards\":3,\"physical_operations\":0}\n";
}
