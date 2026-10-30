#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cstring>
#include <limits>

namespace {
// Same bounded-evidence compiler support contract as DigitalPotControl; no
// Core binary body is provided. All binary32 bit patterns have defined output.
int parameterInteger(float value) {
  static_assert(sizeof(float) == sizeof(std::uint32_t));
  static_assert(std::numeric_limits<float>::is_iec559 &&
                std::numeric_limits<float>::digits == 24);
  static_assert(sizeof(int) == sizeof(std::int32_t));
  std::uint32_t word;
  std::memcpy(&word, &value, sizeof word);
  const auto exponent = (word >> 23) & 255U;
  const auto fraction = word & 0x7fffffU;
  const bool negative = (word >> 31) != 0;
  if (exponent == 255 && fraction != 0)
    return 0;
  if (exponent < 127)
    return 0;
  if (exponent >= 158)
    return negative ? std::numeric_limits<int>::min()
                    : std::numeric_limits<int>::max();
  std::uint32_t magnitude = 0x800000U | fraction;
  if (exponent >= 150)
    magnitude <<= exponent - 150;
  else
    magnitude >>= 150 - exponent;
  const int integer = static_cast<int>(magnitude);
  return negative ? -integer : integer;
}
constexpr int blinkTag = 0x626c6e6b;
} // namespace

namespace presonus::surface_panel_port {
LEDDispatchState &ledDispatchState() {
  static LEDDispatchState state;
  return state;
}
} // namespace presonus::surface_panel_port

namespace Presonus::Panel {
LEDControl::LEDControl(int tag, int group, int match)
    : Control(tag), color_(17), dirty_(0), savedBlink_(0), group_(group),
      match_(match), blink_(0), on_(1), off_(0) {}
LEDControl::~LEDControl() = default;
void *LEDControl::castTo(int type) {
  return type == 0x4c656443 || type == 0x4374726c ? this : nullptr;
}
void LEDControl::setInverseMode(bool inverse) {
  on_ = inverse ? 0 : 1;
  off_ = inverse ? 1 : 0;
  if (auto *p = getParameter())
    p->changed();
}
void LEDControl::paramChanged(Core::Portable::Parameter *parameter,
                              int message) {
  Control::paramChanged(parameter, message);
  if (message == Core::Portable::Parameter::kDestroyed)
    return;
  const float value = parameter ? parameter->getValue() : 0.f;
  const bool active =
      match_ == -1 ? value > 0.f : parameterInteger(value) == match_;
  const int selected = active ? on_ : off_;
  if (blink_ == 3 || (blink_ == 1 && selected == off_) ||
      (blink_ == 2 && selected == on_))
    broadcastValue(2);
  else
    broadcastValue(selected);
}
void LEDControl::startBlinking(float seconds) {
  stopTimer(blinkTag);
  savedBlink_ = blink_;
  setBlinkMode(static_cast<BlinkMode>(3));
  if (seconds > 0.f)
    startTimer(seconds, blinkTag);
}
void LEDControl::stopBlinking() {
  stopTimer(blinkTag);
  setBlinkMode(static_cast<BlinkMode>(savedBlink_));
}
void LEDControl::timerCallback(int tag) {
  if (tag == blinkTag)
    stopBlinking();
}
void LEDControl::transmit() {
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  if (dispatch.disabled) {
    if (!dispatch.dirty.contains(this))
      dispatch.dirty.add(this);
    return;
  }
  if (auto *io = presonus::panel::ControlAccess::io(*this)) {
    Uart_Msg_Type level{
        {0x4c, static_cast<std::uint8_t>(group_),
         static_cast<std::uint8_t>(presonus::panel::ControlAccess::tag(*this)),
         static_cast<std::uint8_t>(
             presonus::panel::ControlAccess::lastLevel(*this))}};
    io->writeMsg(level);
    if (dirty_) {
      if (color_ != 17) {
        Uart_Msg_Type color{{0x72, static_cast<std::uint8_t>(group_),
                             static_cast<std::uint8_t>(
                                 presonus::panel::ControlAccess::tag(*this)),
                             static_cast<std::uint8_t>(color_)}};
        io->writeMsg(color);
      }
      dirty_ = 0;
    }
  }
}
} // namespace Presonus::Panel
