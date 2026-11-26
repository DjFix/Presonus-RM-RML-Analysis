#include "presonus/panel/meter_level_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace {
int toInt(float value) {
  if (!std::isfinite(value) || value < -2147483648.f || value >= 2147483648.f)
    throw std::domain_error("meter requires finite int32 conversion");
  return static_cast<int>(value);
}
} // namespace

namespace Presonus::Panel {

MeterLevelControl::MeterLevelControl(int tag) : MeterControl(tag) {}

MeterLevelControl::~MeterLevelControl() = default;

void *MeterLevelControl::castTo(int type) {
  constexpr int meterLevelControl = 0x4d4c436c;
  if (type == meterLevelControl)
    return this;
  return MeterControl::castTo(type);
}

int MeterLevelControl::getParameterMode() const { return parameterMode_; }

int MeterLevelControl::getNumMeterSteps(bool alternate) const {
  if (parameterMode_ == 12)
    return 255;
  const auto direction =
      presonus::surface_panel_port::MeterControlAccess::direction(*this);
  return MeterControl::getNumMeterSteps(static_cast<BusDirection>(direction),
                                        false) +
         (alternate && getAltParameter() ? 1 : 0);
}
bool MeterLevelControl::setParameter(Core::Portable::Parameter *parameter,
                                     int mode) {
  const bool changed = parameterMode_ != mode;
  parameterMode_ = mode;
  if (Control::setParameter(parameter, 0))
    return true;
  if (!changed)
    return false;
  paramChanged(getParameter(), 3);
  return true;
}
bool MeterLevelControl::setClipParameter(Core::Portable::Parameter *parameter) {
  return setAltParameter(parameter);
}
void MeterLevelControl::paramChanged(Core::Portable::Parameter *parameter,
                                     int action) {
  Control::paramChanged(parameter, action);
  if (action != 3 || presonus::panel::ControlAccess::tag(*this) < 0)
    return;
  if (parameter == getAltParameter()) {
    transmit();
    return;
  }
  const float normalized =
      getParameter() ? getParameter()->getNormalized() : 0.f;
  const auto direction =
      presonus::surface_panel_port::MeterControlAccess::direction(*this);
  const auto &table =
      customTable_
          ? *customTable_
          : (direction == 0
                 ? presonus::surface_panel_port::MeterControlAccess::input()
                 : presonus::surface_panel_port::MeterControlAccess::output());
  const int count = MeterControl::getNumMeterSteps(
      static_cast<BusDirection>(direction), false);
  int step;
  switch (parameterMode_) {
  case 0:
    step = table.getStepFromGain(normalized);
    break;
  case 1:
    step = table.getStepFromGain(1.f - normalized);
    break;
  case 13:
    step = table.getStepFromNormalizedDB(normalized);
    break;
  case 9: {
    const float inverted = 1.f - normalized;
    step = inverted < 0.001f ? 0
           : inverted > 0.99f
               ? count
               : toInt(static_cast<float>(count - 1) * inverted) + 1;
    if (step == count)
      ++step;
    break;
  }
  case 4:
    step = toInt(normalized * static_cast<float>(count - 1));
    break;
  case 2:
    step = toInt(static_cast<float>(count - 1) * normalized);
    if ((count & 1) == 0)
      ++step;
    break;
  case 11:
    step = toInt(normalized * static_cast<float>(count));
    break;
  case 12:
    step = toInt(normalized * 255.f);
    break;
  default:
    step = toInt(normalized * static_cast<float>(count - 1)) + 1;
    break;
  }
  broadcastValue(step);
}
void MeterLevelControl::broadcastValue(int value) {
  const int level =
      std::max(0, std::min(value, getNumMeterSteps(true))) + levelOffset_;
  bool blank = !getParameter() || !getParameter()->isEnabled();
  if (parameterMode_ == 6 || parameterMode_ == 7)
    blank = false;
  auto &last = presonus::panel::ControlAccess::lastLevel(*this);
  if (last == level && transmittedMode_ == parameterMode_ && blank_ == blank &&
      (!getAltParameter() ||
       clipActive_ == (getAltParameter()->getValue() != 0.f)))
    return;
  transmittedMode_ = parameterMode_;
  last = level;
  blank_ = blank;
  transmit();
}
void MeterLevelControl::transmit() {
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  if (dispatch.disabled && getParameter() &&
      std::strncmp(getParameter()->getName(), "meter", 5) != 0) {
    auto &queue = dispatch.dirty;
    if (!queue.contains(this) && (queue.count() < queue.getCapacity() ||
                                  queue.resize(queue.count() + 1)))
      queue.add(this);
    return;
  }
  int mode = transmittedMode_;
  if (mode == 8 || mode == 11 || mode == 13)
    mode = 0;
  else if (mode == 9 || mode == 10)
    mode = 1;
  auto *io = presonus::panel::ControlAccess::io(*this);
  // Native code requires an attached IPanelIO; reject an invalid portable
  // caller.
  if (!io)
    throw std::logic_error("meter transmit requires IPanelIO");
  const auto tag =
      static_cast<unsigned char>(presonus::panel::ControlAccess::tag(*this));
  Uart_Msg_Type message{
      {0x56, tag,
       static_cast<unsigned char>(
           blank_ ? 0 : presonus::panel::ControlAccess::lastLevel(*this)),
       static_cast<unsigned char>(blank_ ? 0 : mode)}};
  io->writeMsg(message);
  clipActive_ = getAltParameter() && toInt(getAltParameter()->getValue()) > 0;
  if (getAltParameter() &&
      (clipActive_ || transmittedMode_ == 9 || transmittedMode_ == 10)) {
    Uart_Msg_Type clip{{0x4e, tag,
                        static_cast<unsigned char>(
                            static_cast<unsigned char>(getNumMeterSteps(true)) +
                            levelOffset_ - 1),
                        static_cast<unsigned char>(clipActive_)}};
    io->writeMsg(clip);
  }
}
} // namespace Presonus::Panel
