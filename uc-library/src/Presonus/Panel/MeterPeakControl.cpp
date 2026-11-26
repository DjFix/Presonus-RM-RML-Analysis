#include "presonus/panel/meter_peak_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include "presonus/surface_panel/MeterControl.hpp"
#include <cstring>

namespace Presonus::Panel {
MeterPeakControl::MeterPeakControl(int tag) : Control(tag) {}
MeterPeakControl::~MeterPeakControl() = default;

void *MeterPeakControl::castTo(int type) {
  if (type == 0x5043746c || type == 0x4d43746c)
    return this;
  return Control::castTo(type);
}
void MeterPeakControl::paramChanged(Core::Portable::Parameter *parameter,
                                    int message) {
  Control::paramChanged(parameter, message);
  if (message != Core::Portable::Parameter::kChanged ||
      presonus::panel::ControlAccess::tag(*this) < 0)
    return;
  const float value = parameter->getValue();
  const auto &table =
      scaleTable_
          ? *scaleTable_
          : (scaleMode_ == 0
                 ? presonus::surface_panel_port::MeterControlAccess::input()
                 : presonus::surface_panel_port::MeterControlAccess::output());
  broadcastValue(table.getStepFromGain(value));
}

void MeterPeakControl::broadcastValue(int value) {
  if (static_cast<std::uint32_t>(value) > 16U)
    return;
  const std::uint32_t word = static_cast<std::uint32_t>(value) +
                             static_cast<std::uint32_t>(peakOffset_);
  int adjusted;
  static_assert(sizeof adjusted == sizeof word);
  std::memcpy(&adjusted, &word, sizeof adjusted);
  auto &level = presonus::panel::ControlAccess::lastLevel(*this);
  if (level == adjusted)
    return;
  level = adjusted;
  transmit();
}

void MeterPeakControl::transmit() {
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  if (dispatch.disabled) {
    if (!dispatch.dirty.contains(this))
      dispatch.dirty.add(this);
    return;
  }
  // Native direct path requires attached IO; caller retains that precondition.
  auto *io = presonus::panel::ControlAccess::io(*this);
  Uart_Msg_Type message{
      {0x4f,
       static_cast<std::uint8_t>(presonus::panel::ControlAccess::tag(*this)),
       static_cast<std::uint8_t>(
           presonus::panel::ControlAccess::lastLevel(*this)),
       0}};
  io->writeMsg(message);
}
} // namespace Presonus::Panel
