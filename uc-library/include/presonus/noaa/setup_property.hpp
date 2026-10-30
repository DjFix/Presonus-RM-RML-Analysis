#pragma once
#include "core/public/coreproperty.h"
#include "presonus/noaa/router_slot_tables.hpp"
#include <cstdint>
namespace presonus::noaa {
// Independent native opaque reference. Original field type/const/ownership is
// unresolved. Never dereferenced or adjusted by an ARM byte offset on the host.
struct OpaqueSetupReference {
  const void *value;
};
} // namespace presonus::noaa
namespace Presonus::NOAA {
// Evidence-backed portable app property using the actual upstream base.
// Original ARM output is36bytes; native pointers/alignment/size differ. Unknown
// fields keep observed-offset labels instead of invented original declarations.
struct NOAASetupProperty : Core::Property {
  static constexpr Core::PropertyType kID = FOUR_CHAR_ID('s', 'e', 't', 'u');
  NOAASetupProperty(const char *path,
                    presonus::noaa::OpaqueSetupReference alreadyAdjusted0c,
                    const presonus::noaa::RouterSlotTables &slots,
                    std::uint32_t observed1c,
                    presonus::noaa::OpaqueSetupReference native20)
      : Core::Property(kID, sizeof(NOAASetupProperty)), spiPath(path),
        opaque0c(alreadyAdjusted0c), slotTables(slots),
        observedWord1c(observed1c), opaque20(native20) {}
  const char *spiPath;
  presonus::noaa::OpaqueSetupReference opaque0c;
  presonus::noaa::RouterSlotTables slotTables;
  std::uint32_t observedWord1c;
  presonus::noaa::OpaqueSetupReference opaque20;
};
} // namespace Presonus::NOAA
