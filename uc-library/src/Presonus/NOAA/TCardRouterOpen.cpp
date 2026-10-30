#include "presonus/noaa/router.hpp"
#include "presonus/noaa/setup_property.hpp"
namespace Presonus::NOAA {
// Source-port bool only: original ordinary return declaration remains pending.
bool TCardRouter::open(const NOAASetupProperty &property) {
  diagnostics_.diagnostic(false, "router open", 0, false);
  // Original copies3tablepointers, not a pointer to its property temporary.
  state_.ownedSlotTables.emplace(property.slotTables);
  state_.slotTables = &*state_.ownedSlotTables;
  return true;
}
} // namespace Presonus::NOAA
