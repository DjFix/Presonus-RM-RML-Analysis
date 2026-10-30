#include "presonus/panel/motorized_fader_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace {
int boundedFloatToInt(float value) {
  // Normal actual-parameter domain; NaN/infinite/out-of-int32 ARM conversion
  // remains explicitly outside this source-port proof, never C++ UB.
  if (!std::isfinite(value) || value < -2147483648.0f || value >= 2147483648.0f)
    throw std::domain_error(
        "finite in-range original fader conversion required");
  return static_cast<int>(value);
}
} // namespace
namespace presonus::panel {
Core::Vector<Presonus::Panel::Control *> &motorizedDeferredControls() {
  return presonus::surface_panel_port::ledDispatchState().dirty;
}
} // namespace presonus::panel
namespace Presonus::Panel {
MotorizedFaderControl::MotorizedFaderControl(int tag) : FaderControl(tag) {}
MotorizedFaderControl::~MotorizedFaderControl() = default;
void *MotorizedFaderControl::castTo(int tag) {
  return tag == 0x4d6f7443 ? this : FaderControl::castTo(tag);
}
void MotorizedFaderControl::broadcastValue(int value) {
  auto &level = presonus::panel::ControlAccess::lastLevel(*this);
  if (level != value) {
    level = value;
    transmit();
  }
}
void MotorizedFaderControl::transmit() {
  if (receiving_)
    return;
  if (presonus::surface_panel_port::ledDispatchState().disabled) {
    auto &queue = presonus::panel::motorizedDeferredControls();
    for (int i = 0; i < queue.count(); ++i)
      if (queue.at(i) == this)
        return;
    if (queue.count() < queue.getCapacity() || queue.resize(queue.count() + 1))
      queue.add(this);
    return;
  }
  if (auto *io = presonus::panel::ControlAccess::io(*this)) {
    const auto value =
        static_cast<unsigned>(presonus::panel::ControlAccess::lastLevel(*this));
    Uart_Msg_Type message{
        {0x66,
         static_cast<unsigned char>(presonus::panel::ControlAccess::tag(*this)),
         static_cast<unsigned char>(value),
         static_cast<unsigned char>(value >> 8)}};
    io->writeMsg(message);
  }
}
void MotorizedFaderControl::paramChanged(Core::Portable::Parameter *parameter,
                                         int message) {
  Control::paramChanged(parameter, message);
  if (message == 3)
    broadcastValue(boundedFloatToInt(parameter->getNormalized() * 1024.0f));
}
void MotorizedFaderControl::receiveValue(int value) {
  if (!getParameter())
    return;
  const auto saved = receiving_;
  receiving_ = 1;
  try {
    FaderControl::receiveValue(value);
    if (touched_)
      lastInput_ = value;
    auto *parameter = getParameter();
    if (!parameter)
      presonus::panel::ControlAccess::lastLevel(*this) = -1;
    else if (auto *alias = Core::Portable::AliasParam::cast(parameter);
             alias && !alias->getOriginal())
      presonus::panel::ControlAccess::lastLevel(*this) = -1;
  } catch (...) {
    receiving_ = saved;
    throw;
  }
  receiving_ = saved;
}
void MotorizedFaderControl::handleTouch(bool touched) {
  if (auto *parameter = getParameter()) {
    if (touched) {
      touched_ = 1;
      lastInput_ = boundedFloatToInt(parameter->getValue());
    } else {
      touched_ = 0;
      parameter->setValue(static_cast<float>(lastInput_), false);
    }
  }
  FaderControl::handleTouch(touched);
}
} // namespace Presonus::Panel
