#include "presonus/mixer/setup_property_applications.hpp"
#include "presonus/noaa/router.hpp"
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
using namespace presonus::noaa;
using namespace presonus::dice;
using namespace Presonus::NOAA;
using namespace Presonus::Mixer;
static_assert(std::is_base_of<Core::Property, NOAASetupProperty>::value);
static_assert(std::is_abstract<GambitApplication>::value &&
              std::is_abstract<BeastApplication>::value &&
              std::is_abstract<StormApplication>::value &&
              std::is_abstract<RogueApplication>::value &&
              std::is_abstract<WolverineApplication>::value);
static_assert(!std::is_default_constructible<GambitApplication>::value);
template <class T> struct CapturedApplication final : T {
  using T::T;
  void onProgress(const char *, float) override { std::abort(); }
  bool isNetworkClientReady() const override { std::abort(); }
  Presonus::UC::ClientRootComponent *
  createClientComponent(const Presonus::UC::NetworkItem &) override {
    std::abort();
  }
  void releaseClientComponent(Presonus::UC::ClientRootComponent *) override {
    std::abort();
  }
};
extern "C" __attribute__((noinline)) NOAASetupProperty
setup_property_virtual_get(const MixerApplication *app) {
  return app->getNOAASetupProperty();
}
static NOAASetupProperty get(const std::string &model,
                             const presonus::mixer::SetupContext &context) {
  using presonus::mixer::setupContextTag;
  if (model == "Gambit") {
    CapturedApplication<GambitApplication> app(setupContextTag, context);
    return setup_property_virtual_get(&app);
  }
  if (model == "Beast") {
    CapturedApplication<BeastApplication> app(setupContextTag, context);
    return setup_property_virtual_get(&app);
  }
  if (model == "Storm") {
    CapturedApplication<StormApplication> app(setupContextTag, context);
    return setup_property_virtual_get(&app);
  }
  if (model == "Rogue") {
    CapturedApplication<RogueApplication> app(setupContextTag, context);
    return setup_property_virtual_get(&app);
  }
  assert(model == "Wolverine");
  CapturedApplication<WolverineApplication> app(setupContextTag, context);
  return setup_property_virtual_get(&app);
}
static const RouterSlotTables &slots(const std::string &model) {
  if (model == "Gambit")
    return rm13731GambitRouterSlots();
  if (model == "Beast")
    return rm13731BeastRouterSlots();
  if (model == "Storm")
    return rm13731StormRouterSlots();
  if (model == "Rogue")
    return rm13731RogueRouterSlots();
  assert(model == "Wolverine");
  return rm13731WolverineRouterSlots();
}
static void same(const RouterSlotTables &a, const RouterSlotTables &b) {
  assert(a.adcBytes() == b.adcBytes() && a.dacBytes() == b.dacBytes() &&
         a.geqBytes() == b.geqBytes());
}
struct Response final : ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : SpiServiceIO {
  RouterState *state = nullptr;
  const RouterSlotTables *expectedBefore = nullptr;
  const unsigned char *beforeADC = nullptr;
  const unsigned char *beforeDAC = nullptr;
  const unsigned char *beforeGEQ = nullptr;
  void captureBefore() {
    expectedBefore = state->slotTables;
    if (expectedBefore) {
      beforeADC = expectedBefore->adcBytes();
      beforeDAC = expectedBefore->dacBytes();
      beforeGEQ = expectedBefore->geqBytes();
    }
  }
  unsigned logs = 0;
  bool fail = false;
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const SpiTransfer &) override { std::abort(); }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool out, const char *fmt, int value, bool arg) override {
    assert(!out && std::strcmp(fmt, "router open") == 0 && value == 0 && !arg);
    assert(state && state->slotTables == expectedBefore);
    if (expectedBefore)
      assert(state->slotTables->adcBytes() == beforeADC &&
             state->slotTables->dacBytes() == beforeDAC &&
             state->slotTables->geqBytes() == beforeGEQ);
    ++logs;
    if (fail)
      throw std::runtime_error("log boundary failure");
  }
};
int main(int argc, char **argv) {
  std::ifstream file;
  if (argc > 1) {
    file.open(argv[1]);
    assert(file);
    std::cin.rdbuf(file.rdbuf());
  }
  RouterState state{};
  Response response;
  IO io;
  io.state = &state;
  TCardRouter router(state, response, io, rm13731LinkAddressRouterLookup());
  std::string line;
  unsigned getters = 0, opens = 0;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    char kind;
    std::string model;
    std::uint32_t opaque0c, opaque20, scalar, tag, originalSize;
    in >> kind >> model;
    if (kind == 'G') {
      in >> opaque0c >> opaque20 >> scalar;
      assert(!in.fail());
      // Fixture boundary supplies already-adjusted opaque tokens. This does not
      // apply ARM+0xb0 to a native object or claim a pointer ABI match.
      presonus::mixer::SetupContext context(
          {reinterpret_cast<const void *>(std::uintptr_t(opaque0c))},
          {reinterpret_cast<const void *>(std::uintptr_t(opaque20))});
      auto p = get(model, context);
      assert(p.type == NOAASetupProperty::kID && p.size == sizeof(p));
      assert(std::strcmp(p.spiPath, "/dev/spidev0.3") == 0);
      assert(p.opaque0c.value == context.alreadyAdjusted0c.value &&
             p.opaque20.value == context.native20.value);
      assert(p.observedWord1c == scalar);
      same(p.slotTables, slots(model));
      ++getters;
    } else {
      assert(kind == 'O');
      in >> tag >> originalSize;
      assert(!in.fail());
      presonus::mixer::SetupContext context({nullptr}, {nullptr});
      io.captureBefore();
      const auto before = state.applicationBytes;
      {
        auto p = get(model, context);
        // Original open ignores the incoming header; preserve this behavior.
        p.type = static_cast<Core::PropertyType>(tag);
        p.size = static_cast<int>(originalSize);
        assert(router.open(p));
        assert(state.ownedSlotTables.has_value() &&
               state.slotTables == &*state.ownedSlotTables);
      }
      // Property lifetime ended. The retained VIEW is State-owned, while the
      // immutable model bytes themselves have independent static lifetime.
      same(*state.slotTables, slots(model));
      assert(router.lookupADCSlot(slots(model).adcBytes()[0]) == 0);
      assert(router.lookupDACSlot(slots(model).dacBytes()[0]) == 0);
      assert(router.lookupGeqSlot(slots(model).geqBytes()[0]) == 0);
      assert(state.applicationBytes == before);
      ++opens;
    }
  }
  std::uint64_t native0 = 1, native1 = 2;
  presonus::mixer::SetupContext nativeContext({&native0}, {&native1});
  auto property = get("Gambit", nativeContext);
  assert(property.opaque0c.value == &native0 &&
         property.opaque20.value == &native1);
  io.captureBefore();
  io.fail = true;
  const auto *binding = state.slotTables;
  bool threw = false;
  try {
    router.open(property);
  } catch (const std::runtime_error &) {
    threw = true;
  }
  assert(threw && state.slotTables == binding);
  assert(getters == 320 && opens == 60 && io.logs == 61);
  std::cout << "{\"passed\":true,\"getter_cases\":" << getters
            << ",\"open_cases\":" << opens
            << ",\"native_property_size\":" << sizeof(NOAASetupProperty)
            << ",\"native_pointer_bytes\":" << sizeof(void *)
            << ",\"temporary_view_lifetime\":true,\"partial_apps_abstract\":"
               "true,\"physical_open_calls\":0}\n";
}
