#include "presonus/noaa/router.hpp"
#include "presonus/noaa/router_slot_tables.hpp"
#include <stdexcept>
namespace {
unsigned char lookup(const unsigned char *table, unsigned count,
                     unsigned char value) {
  for (unsigned index = 0; index < count; ++index)
    if (table[index] == value)
      return static_cast<unsigned char>(index);
  return 0xff;
}
const presonus::noaa::RouterSlotTables &
requireTables(const presonus::noaa::RouterState &state) {
  if (!state.slotTables)
    throw std::logic_error(
        "Router lookup requires explicit immutable slot tables");
  return *state.slotTables;
}
} // namespace
namespace Presonus::NOAA {
// Portable return choice only; original ordinary declarations remain pending.
unsigned char TCardRouter::lookupADCSlot(unsigned char value) {
  return lookup(requireTables(state_).adcBytes(), 40, value);
}
unsigned char TCardRouter::lookupDACSlot(unsigned char value) {
  return lookup(requireTables(state_).dacBytes(), 24, value);
}
unsigned char TCardRouter::lookupGeqSlot(unsigned char value) {
  return lookup(requireTables(state_).geqBytes(), 16, value);
}
} // namespace Presonus::NOAA
