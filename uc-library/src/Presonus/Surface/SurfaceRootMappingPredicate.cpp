#include "presonus/surface_panel/ControlHelpers.hpp"
#include <initializer_list>

// Bind the actual libc providers. libstdc++ std::strstr overloads call an
// explicit compiler builtin even under -fno-builtin; at O3 that can remove
// the original provider observations. Distinct C++ identifiers with ELF
// assembler labels preserve real external calls without disabling optimization.
extern "C" char *surfaceMappingStrstr(const char *, const char *) asm("strstr");
extern "C" int surfaceMappingStrcmp(const char *, const char *) asm("strcmp");

namespace Presonus::Surface {
bool SurfaceRootComponent::isMappableControl(const char *controlName) {
  const char *name = controlName ? controlName : "";
  bool result = false;
  // Preserve all five original provider comparisons, including null input.
  for (const char *prefix :
       {"transport_", "mod_", "fx_mixselect", "strip_mixselect", "mapping_"}) {
    const char *match = surfaceMappingStrstr(name, prefix);
    result |= match == name;
  }
  if (controlName)
    for (const char *exact : {"main_mix", "fx_tap", "quick_recall", "marker"})
      result |= surfaceMappingStrcmp(controlName, exact) == 0;
  return result;
}
} // namespace Presonus::Surface
