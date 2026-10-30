#pragma once
#include "presonus/surface_panel/LEDState.hpp"
#include <cstdint>

namespace Presonus::Panel {
class SwitchControl;
}
namespace presonus::panel_binding {
struct SwitchAccess;
// Independent operation callbacks. These names/types are not an original
// receiver interface or evidence of its class identity/ABI. Callbacks require
// live borrowed context, are nonthrowing and cannot mutate/reenter the control.
struct SwitchDispatchCallbacks {
  std::uint32_t (*allowDown)(void *, Presonus::Panel::SwitchControl &);
  std::uint32_t (*immediate)(void *, Presonus::Panel::SwitchControl &);
  float (*holdSeconds)(void *, Presonus::Panel::SwitchControl &);
  void (*held)(void *, Presonus::Panel::SwitchControl &);
  void (*down)(void *, Presonus::Panel::SwitchControl &);
  void (*up)(void *, Presonus::Panel::SwitchControl &);
};
struct SwitchDetachBoundary {
  void *context;
  void (*detach)(void *, Presonus::Panel::SwitchControl &);
  // Null remains valid for lifecycle-only uses. Nonnull receiver in the new
  // operational methods requires all six callbacks in a live dispatch table.
  SwitchDispatchCallbacks *dispatch = nullptr;
};
void resetSwitchParameter(Core::Portable::Parameter &);
// Independent call boundary, implemented solely through genuine CCL APIs.
// Operations: 0=isEnabled,1=getMax,2=getValue,3=setValue(value,true),
// 4=increment(1),5=beginEdit,6=endEdit. Float results/arguments retain raw
// bits.
std::uint32_t switchParameterDispatch(Core::Portable::Parameter &, unsigned,
                                      std::uint32_t = 0);
} // namespace presonus::panel_binding

namespace Presonus::Panel {
// Original RTTI-proven LEDControl base; portable logical representation.
// Ordinary return declarations and receiver identity remain unresolved.
class SwitchControl : public LEDControl {
public:
  SwitchControl(int, int, bool);
  ~SwitchControl() override;
  void *castTo(int) override;
  std::uint8_t isImmediate() const;
  void setImmediate(bool);
  void disableControl(bool, bool) override;
  void switchDown();
  void switchUp();
  void doSwitch();
  void timerCallback(int) override;

private:
  std::uint8_t pressed_;
  std::uint8_t immediate_;
  std::uint8_t disabled_;
  presonus::panel_binding::SwitchDetachBoundary *receiver_;
  std::uint8_t held_;
  friend struct presonus::panel_binding::SwitchAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel_binding {
struct SwitchAccess {
  static auto &pressed(Presonus::Panel::SwitchControl &v) { return v.pressed_; }
  static auto &immediate(Presonus::Panel::SwitchControl &v) {
    return v.immediate_;
  }
  static auto &disabled(Presonus::Panel::SwitchControl &v) {
    return v.disabled_;
  }
  static auto &receiver(Presonus::Panel::SwitchControl &v) {
    return v.receiver_;
  }
  static auto &held(Presonus::Panel::SwitchControl &v) { return v.held_; }
};
} // namespace presonus::panel_binding
