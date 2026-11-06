#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstring>

namespace Presonus::Surface {
bool SurfaceRootComponent::isMappableControl(const char *controlName) {
  const char *name = controlName ? controlName : "";
  bool result = false;
  // Preserve all five original provider comparisons, including null input.
  for (const char *prefix :
       {"transport_", "mod_", "fx_mixselect", "strip_mixselect", "mapping_"}) {
    const char *match = std::strstr(name, prefix);
    result |= match == name;
  }
  if (controlName)
    for (const char *exact : {"main_mix", "fx_tap", "quick_recall", "marker"})
      result |= std::strcmp(controlName, exact) == 0;
  return result;
}
} // namespace Presonus::Surface
