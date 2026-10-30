#pragma once
#include "core/portable/coreparams.h"
#include <cstdint>

// Portable class declarations for the evidenced methods only. These do
// not reproduce original inheritance, object storage, vtables or ARM32 layouts.
namespace presonus::panel_binding {
struct RegistrarGroupRegistry;
}
namespace Presonus::Panel {
class ControlGroup;
class ControlRegistrar {
public:
  // Independent borrowed setup only; original lifecycle/layout unresolved.
  ControlRegistrar() = default;
  explicit ControlRegistrar(
      presonus::panel_binding::RegistrarGroupRegistry &state)
      : groupRegistry_(&state) {}
  // Original return spellings are unencoded; these are portable declarations.
  int count() const;
  ControlGroup *at(int index) const;
  // Original nested enum identity is encoded in the method's mangled name.
  // Original enumerator names/range/underlying declaration are unresolved;
  // the portable int32 domain preserves the observed ARM register behavior.
  enum ControlType : int {};

private:
  presonus::panel_binding::RegistrarGroupRegistry *groupRegistry_ = nullptr;
};
class SevenSegControl {
public:
  // The ARM implementation returns a zero-extended 16-bit bitmap. Its exact
  // original C++ return declaration is not encoded in the symbol name.
  std::uint16_t convertCharToBmp(char character, bool decimalPoint) const;
};
} // namespace Presonus::Panel
namespace Presonus {
class IPanelPort;
}
namespace presonus::surface {
// Independent borrowed live port selection, not original registrar fields.
struct PanelRegistrarCommandState {
  Presonus::IPanelPort *port = nullptr;
};
} // namespace presonus::surface
namespace Presonus::Surface {
class PanelRegistrar {
public:
  // Independent constructors; original AppMode lifecycle remains unrecovered.
  PanelRegistrar() = default;
  explicit PanelRegistrar(presonus::surface::PanelRegistrarCommandState &state)
      : commandState_(&state) {}
  // Independent borrowed CCL list adapter; no original layout/lifecycle claim.
  // Both selected tags must exist and yield finite signed32-representable
  // values.
  explicit PanelRegistrar(const Core::Portable::ParamList &parameters)
      : parameters_(&parameters) {}
  // Independent combined borrowed-state constructor; not original lifecycle.
  PanelRegistrar(const Core::Portable::ParamList &parameters,
                 presonus::surface::PanelRegistrarCommandState &state)
      : commandState_(&state), parameters_(&parameters) {}
  // Incidental signed32 result observed; original return spelling unresolved.
  int bumpFaderTouchSensitivity(int delta);
  int bumpFaderSpeed(int delta);
  // Observed signed32 conversion results; original return declarations
  // unresolved.
  int getFaderSensitivity();
  int getFaderSpeed();
  // void returns are portable choices; ordinary original returns are
  // unresolved.
  void sendFaderFunctionMessage(unsigned char);
  void requestUpdatedFaderParameters();
  void invokeFaderCalibration(bool);
  // Observed signed 32-bit mapping result; original return spelling unresolved.
  int mapGroupIdToControlType(
      Presonus::Panel::ControlRegistrar::ControlType group) const;

private:
  presonus::surface::PanelRegistrarCommandState *commandState_ = nullptr;
  const Core::Portable::ParamList *parameters_ = nullptr;
};
class SurfaceRootComponent {
public:
  // Observed 0/1 predicate result; original return spelling unresolved.
  bool isTransportControl(const char *controlName);
};
} // namespace Presonus::Surface
