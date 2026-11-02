#pragma once
#include "core/portable/gui/coreview.h"
#include "presonus/surface/IDisplayPort.hpp"
namespace presonus::surface_display_port {
struct DisplayManagerAccess;
}
namespace Presonus {
// Partial app source model; original constructor/base/layout/returns not
// claimed.
class DisplayManager {
public:
  void flushColorLcdUpdates();
  // Portable choice: original return and static declaration remain unresolved.
  static DisplayManager *getInstance();

private:
  static DisplayManager *theInstance;
  Core::Portable::RootView *root_ = nullptr;
  IDisplayPort *port_ = nullptr;
  bool suspended_ = false;
  friend struct presonus::surface_display_port::DisplayManagerAccess;
};
} // namespace Presonus
namespace presonus::surface_display_port {
struct DisplayManagerAccess {
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
