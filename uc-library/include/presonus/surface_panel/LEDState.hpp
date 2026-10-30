#pragma once
#include "presonus/panel/control.hpp"
#include <array>
#include <cstdint>

enum RGBLedColors : int {};
namespace presonus::surface_panel_port {
struct LEDStateAccess;
struct LEDLifecycleAccess;
// Explicit portable relocation of catalogued Control globals. This storage
// does not define the original static data symbols or their ARM initialization.
struct LEDDispatchState {
  std::uint8_t disabled = 0;
  Core::Vector<Presonus::Panel::Control *> dirty;
};
LEDDispatchState &ledDispatchState();
} // namespace presonus::surface_panel_port

namespace Presonus::Panel {
// RTTI-proven original base. Storage and ordinary return declarations below
// remain a portable source representation, not the original ARM object ABI.
class LEDControl : public Control {
public:
  enum BlinkMode : int {};
  LEDControl(int, int, int);
  ~LEDControl() override;
  void *castTo(int) override;
  void setmatchvalue(int);
  void setBlinkMode(BlinkMode);
  void setColor(RGBLedColors);
  void setFullOff();
  void broadcastValue(int) override;
  void paramChanged(Core::Portable::Parameter *, int) override;
  void transmit() override;
  void startBlinking(float);
  void stopBlinking();
  void timerCallback(int) override;
  void setInverseMode(bool);

private:
  int color_;
  std::uint8_t dirty_;
  int savedBlink_;
  int group_;
  int match_;
  int blink_;
  int on_;
  int off_;
  friend struct presonus::surface_panel_port::LEDStateAccess;
  friend struct presonus::surface_panel_port::LEDLifecycleAccess;
};
} // namespace Presonus::Panel

namespace presonus::surface_panel_port {
struct LEDStateAccess {
  static void setState(Presonus::Panel::LEDControl &v,
                       Core::Portable::Parameter *p,
                       const std::array<std::uint32_t, 5> &s) {
    presonus::panel::ControlAccess::parameter(v) = p;
    presonus::panel::ControlAccess::lastLevel(v) =
        static_cast<std::int32_t>(s[0]);
    v.color_ = static_cast<std::int32_t>(s[1]);
    v.dirty_ = static_cast<std::uint8_t>(s[2]);
    v.match_ = static_cast<std::int32_t>(s[3]);
    v.blink_ = static_cast<std::int32_t>(s[4]);
  }
  static std::array<std::uint32_t, 5>
  state(const Presonus::Panel::LEDControl &v) {
    // Existing Control access is intentionally mutable fixture access only.
    auto &base = const_cast<Presonus::Panel::LEDControl &>(v);
    return {static_cast<std::uint32_t>(
                presonus::panel::ControlAccess::lastLevel(base)),
            static_cast<std::uint32_t>(v.color_), v.dirty_,
            static_cast<std::uint32_t>(v.match_),
            static_cast<std::uint32_t>(v.blink_)};
  }
};
struct LEDLifecycleAccess {
  static auto &savedBlink(Presonus::Panel::LEDControl &v) {
    return v.savedBlink_;
  }
  static auto &group(Presonus::Panel::LEDControl &v) { return v.group_; }
  static auto &on(Presonus::Panel::LEDControl &v) { return v.on_; }
  static auto &off(Presonus::Panel::LEDControl &v) { return v.off_; }
};
} // namespace presonus::surface_panel_port
