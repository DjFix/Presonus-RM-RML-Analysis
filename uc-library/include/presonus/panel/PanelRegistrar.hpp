#pragma once
#include "core/system/corethread.h"
#include "presonus/surface_panel/ControlHelpers.hpp"
namespace presonus::panel_binding {
// Independent borrowed port state, no original registrar layout claim.
struct PanelRegistrarPortState {
  Presonus::IPanelPort *port = nullptr;
};
} // namespace presonus::panel_binding
namespace Presonus::Panel {
// Partial source-port declaration in the original namespace. Original
// lifecycle, inheritance, return declarations and ARM layout remain unresolved.
class PanelRegistrar {
public:
  explicit PanelRegistrar(
      presonus::panel_binding::PanelRegistrarPortState &state)
      : state_(state) {}
  void resetBoard(int mode, int board);
  const char *getPanelPortName();
  Presonus::IPanelPort *getPort() const;
  int mapGroupIdToControlType(ControlRegistrar::ControlType) const;

private:
  presonus::panel_binding::PanelRegistrarPortState &state_;
  // Independent owned CCL lock; no native offset/layout claim.
  Core::Threads::Lock resetLock_;
};
} // namespace Presonus::Panel
