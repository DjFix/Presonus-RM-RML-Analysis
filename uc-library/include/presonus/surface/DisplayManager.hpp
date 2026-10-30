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

private:
  Core::Portable::RootView *root_ = nullptr;
  IDisplayPort *port_ = nullptr;
  bool suspended_ = false;
  friend struct presonus::surface_display_port::DisplayManagerAccess;
};
} // namespace Presonus
namespace presonus::surface_display_port {
struct DisplayManagerAccess {
  static void bind(Presonus::DisplayManager &m, Core::Portable::RootView &root,
                   Presonus::IDisplayPort &port, bool suspended) {
    m.root_ = &root;
    m.port_ = &port;
    m.suspended_ = suspended;
  }
};
} // namespace presonus::surface_display_port
