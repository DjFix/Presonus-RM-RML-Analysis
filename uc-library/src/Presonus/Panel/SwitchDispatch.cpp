#include "presonus/panel/switch_control.hpp"
#include <cstring>
namespace {
constexpr int heldTag = 0x68656c64;
float fromBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
std::uint32_t bitsOf(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}
} // namespace
namespace Presonus::Panel {
void SwitchControl::doSwitch() {
  using presonus::panel_binding::switchParameterDispatch;
  auto *p = getParameter();
  if (disabled_ || !p || !switchParameterDispatch(*p, 0))
    return;
  const auto match =
      presonus::surface_panel_port::LEDStateAccess::state(*this)[3];
  std::int32_t signedMatch;
  std::memcpy(&signedMatch, &match, sizeof(signedMatch));
  if (signedMatch != -1) {
    switchParameterDispatch(*p, 3, bitsOf(static_cast<float>(signedMatch)));
    return;
  }
  if (fromBits(switchParameterDispatch(*p, 1)) > 1.f) {
    const float current = fromBits(switchParameterDispatch(*p, 2));
    const float maximum = fromBits(switchParameterDispatch(*p, 1));
    if (current >= maximum)
      switchParameterDispatch(*p, 3, bitsOf(0.f));
    else
      switchParameterDispatch(*p, 4);
  } else {
    const float current = fromBits(switchParameterDispatch(*p, 2));
    switchParameterDispatch(*p, 3, bitsOf(current == 1.f ? 0.f : 1.f));
  }
}
void SwitchControl::switchDown() {
  if (disabled_)
    return;
  held_ = 0;
  pressed_ = 1;
  if (receiver_) {
    if (!receiver_->dispatch->allowDown(receiver_->context, *this)) {
      pressed_ = 0;
      return;
    }
    receiver_->dispatch->down(receiver_->context, *this);
    const float seconds =
        receiver_->dispatch->holdSeconds(receiver_->context, *this);
    if (seconds > 0.f)
      startTimer(seconds, heldTag);
  }
  std::uint32_t immediate = immediate_;
  std::uint32_t begin = 1;
  if (receiver_)
    immediate = begin =
        receiver_->dispatch->immediate(receiver_->context, *this);
  if (auto *p = getParameter(); p && begin)
    presonus::panel_binding::switchParameterDispatch(*p, 5);
  if (immediate)
    doSwitch();
}
void SwitchControl::switchUp() {
  if (disabled_ || !pressed_)
    return;
  if (receiver_)
    receiver_->dispatch->up(receiver_->context, *this);
  if (held_) {
    if (auto *p = getParameter())
      presonus::panel_binding::switchParameterDispatch(*p, 6);
    return;
  }
  auto &timers = presonus::panel::ControlAccess::timers();
  bool found = false;
  for (int i = 0; i < timers.count(); ++i) {
    auto *timer = timers.at(i);
    if (timer->control == this && timer->tag == heldTag) {
      found = true;
      break;
    }
  }
  std::uint32_t immediate;
  if (found && !receiver_) {
    immediate = immediate_;
  } else {
    if (found) {
      stopTimer(heldTag);
      if (!receiver_->dispatch->immediate(receiver_->context, *this))
        if (auto *p = getParameter())
          presonus::panel_binding::switchParameterDispatch(*p, 5);
    }
    immediate = receiver_
                    ? receiver_->dispatch->immediate(receiver_->context, *this)
                    : immediate_;
  }
  if (!immediate)
    doSwitch();
  if (auto *p = getParameter())
    presonus::panel_binding::switchParameterDispatch(*p, 6);
  pressed_ = 0;
}
void SwitchControl::timerCallback(int tag) {
  if (tag == heldTag && receiver_) {
    receiver_->dispatch->held(receiver_->context, *this);
    held_ = 1;
  }
  LEDControl::timerCallback(tag);
}
} // namespace Presonus::Panel
