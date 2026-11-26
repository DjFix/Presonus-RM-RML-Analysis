#pragma once
#include "core/portable/gui/coreview.h"
#include "core/public/corevector.h"
#include "presonus/surface/IDisplayPort.hpp"
#include <memory>
#include <vector>

struct Touchscreen_Type;
namespace presonus::surface_display_port {
struct DisplayManagerAccess;
}
namespace Presonus {
class DisplayCommandList;
namespace Panel {
class ControlRegistrar;
}
// Portable value model; original field names, enum and layout unresolved.
struct TouchInputEvent {
  int type;
  int screen;
  int x;
  int y;

  // The UART caller supplies four readable bytes. The original return type
  // remains unresolved.
  void fromMsg(Touchscreen_Type &message);
};
// App source port. The original base and object layout remain unresolved.
class DisplayManager {
public:
  // Portable fields for the observed constructor inputs. Original field
  // declarations and the six unconsumed bytes remain unresolved.
  struct DisplaySpecification {
    int width = 0;
    int height = 0;
    Core::BitmapPixelFormat pixelFormat = Core::kBitmapRGBAlpha;
    int extraWidth = 0;
    int extraHeight = 0;
    int extraCount = 0;
    bool useExternalExtras = false;
    bool useFlipRoot = false;
  };

  DisplayManager();
  explicit DisplayManager(const DisplaySpecification &specification);
  virtual ~DisplayManager();
  void flushColorLcdUpdates();
  // Original return unresolved; source-port void choice.
  void screenTouched(const Panel::ControlRegistrar &, TouchInputEvent);
  // Portable choice: original return and static declaration remain unresolved.
  static DisplayManager *getInstance();

private:
  static DisplayManager *theInstance;
  // Independent ownership extension for native destruction observations.
  // Existing root_/port_/touchViews_ bindings remain borrowed. Original LcdView
  // declarations/receiver offsets are not claimed by this source port.
  DisplaySpecification specification_;
  Core::Vector<Core::Portable::RootView *> ownedViews_;
  std::unique_ptr<DisplayCommandList> ownedCommands_;
  void *ownedCommandStorage_ = nullptr;
  Core::Portable::RootView *root_ = nullptr;
  IDisplayPort *port_ = nullptr;
  bool suspended_ = false;
  std::vector<Core::Portable::RootView *> touchViews_;
  friend struct presonus::surface_display_port::DisplayManagerAccess;
};
} // namespace Presonus
namespace presonus::surface_display_port {
struct DisplayManagerAccess {
  static const Presonus::DisplayManager::DisplaySpecification &
  specification(const Presonus::DisplayManager &m) {
    return m.specification_;
  }
  static const Core::Vector<Core::Portable::RootView *> &
  ownedViews(const Presonus::DisplayManager &m) {
    return m.ownedViews_;
  }
  static Core::Portable::RootView *root(const Presonus::DisplayManager &m) {
    return m.root_;
  }
  static Presonus::DisplayCommandList *
  ownedCommands(const Presonus::DisplayManager &m) {
    return m.ownedCommands_.get();
  }
  static bool adoptView(Presonus::DisplayManager &m,
                        Core::Portable::RootView *p) {
    return m.ownedViews_.add(p);
  }
  static void adoptCommandStorage(Presonus::DisplayManager &m, void *p) {
    m.ownedCommandStorage_ = p;
  }
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
