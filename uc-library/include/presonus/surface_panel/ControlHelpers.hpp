#pragma once
#include <cstdint>

// Portable class declarations for the recovered pure methods only. These do
// not reproduce original inheritance, object storage, vtables or ARM32 layouts.
namespace Presonus::Panel {
class ControlRegistrar {
public:
  // Original nested enum identity is encoded in the method's mangled name.
  // Original enumerator names/range/underlying declaration are unresolved;
  // the portable int32 domain preserves the observed ARM register behavior.
  enum ControlType : int {};
};
class SevenSegControl {
public:
  // The ARM implementation returns a zero-extended 16-bit bitmap. Its exact
  // original C++ return declaration is not encoded in the symbol name.
  std::uint16_t convertCharToBmp(char character, bool decimalPoint) const;
};
} // namespace Presonus::Panel
namespace Presonus::Surface {
class PanelRegistrar {
public:
  // Observed signed 32-bit mapping result; original return spelling unresolved.
  int mapGroupIdToControlType(
      Presonus::Panel::ControlRegistrar::ControlType group) const;
};
class SurfaceRootComponent {
public:
  // Observed 0/1 predicate result; original return spelling unresolved.
  bool isTransportControl(const char *controlName);
};
} // namespace Presonus::Surface
