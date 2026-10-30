#include "presonus/noaa/router.hpp"
#include "presonus/noaa/router_slot_tables.hpp"
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace presonus::noaa;
using namespace presonus::dice;
using namespace Presonus::NOAA;
struct Response final : ResponseServices {
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
static const RouterSlotTables &model(const std::string &name) {
  if (name == "Gambit")
    return rm13731GambitRouterSlots();
  if (name == "Beast")
    return rm13731BeastRouterSlots();
  if (name == "Storm")
    return rm13731StormRouterSlots();
  if (name == "Rogue")
    return rm13731RogueRouterSlots();
  if (name == "Wolverine")
    return rm13731WolverineRouterSlots();
  std::abort();
}
static unsigned call(TCardRouter &router, unsigned kind, unsigned value) {
  if (kind == 0)
    return router.lookupADCSlot(static_cast<unsigned char>(value));
  if (kind == 1)
    return router.lookupDACSlot(static_cast<unsigned char>(value));
  assert(kind == 2);
  return router.lookupGeqSlot(static_cast<unsigned char>(value));
}
static std::vector<unsigned char> unhex(const std::string &value) {
  std::vector<unsigned char> out;
  for (std::size_t i = 0; i < value.size(); i += 2)
    out.push_back(static_cast<unsigned char>(
        std::stoul(value.substr(i, 2), nullptr, 16)));
  return out;
}
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
  TCardRouter router(state, response, io, rm13731LinkAddressRouterLookup());
  for (unsigned kind = 0; kind < 3; ++kind) {
    bool threw = false;
    try {
      (void)call(router, kind, 0);
    } catch (const std::logic_error &) {
      threw = true;
    }
    assert(threw);
  }
  unsigned cases = 0, genuine = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string name, hex;
    unsigned kind, value, expected, actualModel;
    input >> name >> kind >> value >> expected >> actualModel >> hex;
    assert(!input.fail());
    auto bytes = unhex(hex);
    assert(bytes.size() == (kind == 0 ? 40u : kind == 1 ? 24u : 16u));
    unsigned char adc[40]{}, dac[24]{}, geq[16]{};
    auto *target = kind == 0 ? adc : kind == 1 ? dac : geq;
    std::copy(bytes.begin(), bytes.end(), target);
    const RouterSlotTables synthetic(adc, dac, geq);
    state.slotTables = actualModel ? &model(name) : &synthetic;
    const auto *actual = kind == 0   ? state.slotTables->adcBytes()
                         : kind == 1 ? state.slotTables->dacBytes()
                                     : state.slotTables->geqBytes();
    assert(std::equal(bytes.begin(), bytes.end(), actual));
    const auto before = state.applicationBytes;
    assert(call(router, kind, value) == expected);
    assert(state.applicationBytes == before);
    ++cases;
    genuine += actualModel;
    state.slotTables = nullptr;
  }
  assert(cases == 6912 && genuine == 3840);
  std::cout << "{\"passed\":true,\"lookup_cases\":" << cases
            << ",\"genuine_model_cases\":" << genuine
            << ",\"missing_binding_guards\":3,\"physical_operations\":0}\n";
}
