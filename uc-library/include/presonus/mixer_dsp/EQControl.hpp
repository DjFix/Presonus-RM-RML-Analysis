#pragma once
namespace presonus::dsp {
// Independent partial-object construction; not an original constructor.
struct EQControlBiquadPortTag {};
} // namespace presonus::dsp
namespace Presonus {
// Only a field-independent leaf interface. Original GUI inheritance, layout,
// virtual table and lifecycle are not represented by this portable class.
class EQControl {
public:
  explicit EQControl(presonus::dsp::EQControlBiquadPortTag) {}
  // Original ordinary return declaration is unresolved; int is provisional.
  // Supported equivalence domain: index >= 0. Original negative indexing is
  // unchecked and deliberately receives no supported behavior claim.
  int getBiquadType(int index) const;
};
} // namespace Presonus
