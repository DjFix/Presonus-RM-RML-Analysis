#pragma once
#include <cstdint>
namespace Presonus::Mixer {
// Independent portable row composition; not an original class/field
// declaration.
struct ReverbSelectTypeMapEntry {
  std::int32_t family;
  std::int32_t index;
  float effectType;
  float value;
  const char *name;
};
// Stateless partial port. Inheritance, constructors/lifecycle and ARM layout
// remain unresolved. Pointer return, const qualification and row type are
// provisional; observed pointer/data behavior does not establish declarations.
class ReverbComponent {
public:
  struct SourcePortConstruction {};
  explicit ReverbComponent(SourcePortConstruction) {}
  virtual const ReverbSelectTypeMapEntry *getSelectTypeMap();
  // Provisional ordinary return spelling; original ARM result bits are known.
  int mapIDs(int);
};
} // namespace Presonus::Mixer
