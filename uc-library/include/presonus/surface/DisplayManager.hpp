#pragma once
#include "core/portable/gui/coreview.h"
#include "presonus/surface/IDisplayPort.hpp"
#include <vector>
namespace presonus::surface_display_port {
struct DisplayManagerAccess;
}
namespace Presonus {
namespace Panel {
class ControlRegistrar;
}
// Portable value model; original field names, enum and layout unresolved.
struct TouchInputEvent {
  int type;
  int screen;
  int x;
  int y;
};
// Partial app source model; original constructor/base/layout/returns not
// claimed.
class DisplayManager {
public:
  void flushColorLcdUpdates();
  // Original return unresolved; source-port void choice.
  void screenTouched(const Panel::ControlRegistrar &, TouchInputEvent);
  // Portable choice: original return and static declaration remain unresolved.
  static DisplayManager *getInstance();

private:
  static DisplayManager *theInstance;
  Core::Portable::RootView *root_ = nullptr;
  IDisplayPort *port_ = nullptr;
  bool suspended_ = false;
  std::vector<Core::Portable::RootView *> touchViews_;
  friend struct presonus::surface_display_port::DisplayManagerAccess;
};
} // namespace Presonus
namespace presonus::surface_display_port {
struct DisplayManagerAccess {
  static void
  bindTouchViews(Presonus::DisplayManager &m,
                 const std::vector<Core::Portable::RootView *> &views) {
    m.touchViews_ = views;
  }
  // Independent binding helper; no original lifecycle/ownership claim.
  static void bindInstance(Presonus::DisplayManager *instance) {
    Presonus::DisplayManager::theInstance = instance;
  }
  static void bind(Presonus::DisplayManager &m, Core::Portable::RootView &root,
                   Presonus::IDisplayPort &port, bool suspended) {
    m.root_ = &root;
    m.port_ = &port;
    m.suspended_ = suspended;
  }
};
} // namespace presonus::surface_display_port
