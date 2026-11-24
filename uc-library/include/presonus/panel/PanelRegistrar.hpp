#pragma once
#include "core/system/corethread.h"
#include "presonus/surface_panel/ControlHelpers.hpp"
namespace presonus::panel_binding {
// Independent borrowed port state, no original registrar layout claim.
struct PanelRegistrarPortState {
  Presonus::IPanelPort *port = nullptr;
  bool secondaryEnabled = false;
  Presonus::IPanelPort *secondaryPort = nullptr;
  // Explicit initialized source-port input for the word consumed by %d.
  // Original field name/declaration/initialization/layout remain unresolved.
  std::int32_t descriptionNumber = 0;
};
} // namespace presonus::panel_binding
namespace Presonus::Panel {
// Partial source-port declaration in the original namespace. Original
// lifecycle, inheritance, return declarations and ARM layout remain unresolved.
class PanelRegistrar : public ControlRegistrar {
public:
  explicit PanelRegistrar(
      presonus::panel_binding::PanelRegistrarPortState &state)
      : state_(state) {}
  // Independent source-port getter, not an original method identity.
  std::int32_t sourcePortDescriptionNumber() const {
    return state_.descriptionNumber;
  }
  void resetBoard(int mode, int board);
  void onProgress(const char *, float);
  void bootComplete();
  void enableAMP(bool);
  const char *getPanelPortName();
  Presonus::IPanelPort *getPort() const override;
  void writeDualMsg(Uart_Msg_Type &) override;
  int mapGroupIdToControlType(ControlRegistrar::ControlType) const;

private:
  presonus::panel_binding::PanelRegistrarPortState &state_;
  // Independent owned CCL lock; no native offset/layout claim.
  Core::Threads::Lock resetLock_;
};
} // namespace Presonus::Panel
