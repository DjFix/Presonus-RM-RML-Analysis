#pragma once
#include <cstdint>

namespace Presonus {
// Portable enum declaration: encoded original type identity is known; original
// enumerator names and enum declaration are unresolved.
enum class EffectType : std::int32_t {};
namespace Mixer {
// Independent portable representation of the application table. These member
// names/types are source-port choices, not recovered original C++ declarations.
struct DelaySelectTypeMapEntry {
  std::int32_t family;
  std::int32_t index;
  float effectType;
  float value;
  const char *name;
};
// Stateless partial source port of three encoded original methods. No original
// FX inheritance, constructor, lifecycle, object layout or ARM ABI is claimed.
class DelayComponent {
public:
  struct SourcePortConstruction {};
  explicit DelayComponent(SourcePortConstruction) {}
  // All return declarations remain provisional: ordinary mangling omits them.
  std::int32_t mapIDs(int id);
  const DelaySelectTypeMapEntry *getSelectTypeMap();
  std::int32_t getEffectTypeInternal(Presonus::EffectType type);
};
} // namespace Mixer
} // namespace Presonus
