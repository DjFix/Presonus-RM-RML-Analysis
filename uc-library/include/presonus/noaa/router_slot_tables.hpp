#pragma once
namespace presonus::noaa {
// Independent immutable, borrowed table view. Exact extents follow original
// byte-search bounds; this is NOT a fabricated NOAASetupProperty declaration.
class RouterSlotTables {
public:
  constexpr RouterSlotTables(const unsigned char (&adc)[40],
                             const unsigned char (&dac)[24],
                             const unsigned char (&geq)[16])
      : adc_(adc), dac_(dac), geq_(geq) {}
  const unsigned char *adcBytes() const { return adc_; }
  const unsigned char *dacBytes() const { return dac_; }
  const unsigned char *geqBytes() const { return geq_; }

private:
  const unsigned char *const adc_;
  const unsigned char *const dac_;
  const unsigned char *const geq_;
};
// Genuine application-model arrays from the RM13731 ELF. Factories are
// independent source-port APIs; original Mixer getters/open remain unresolved.
const RouterSlotTables &rm13731GambitRouterSlots();
const RouterSlotTables &rm13731BeastRouterSlots();
const RouterSlotTables &rm13731StormRouterSlots();
const RouterSlotTables &rm13731RogueRouterSlots();
const RouterSlotTables &rm13731WolverineRouterSlots();
} // namespace presonus::noaa
