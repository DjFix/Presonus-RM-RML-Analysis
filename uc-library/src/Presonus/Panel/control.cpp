#include "presonus/panel/control.hpp"
#include "presonus/dice/packet_services.hpp"
#include "presonus/panel/param_edit_handler.hpp"
#include <cstring>

namespace {
std::int64_t currentMilliseconds() {
  // Actual CCL nanosecond clock gateway, preserving signed truncation toward 0.
  return presonus::dice::packetClockRawTicks() / 1000000;
}
std::int64_t wrapAdd(std::int64_t a, std::int64_t b) {
  const auto bits =
      static_cast<std::uint64_t>(a) + static_cast<std::uint64_t>(b);
  std::int64_t value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
} // namespace

namespace Presonus::Panel {
// Original local object identity is present in both ELFs. Actual source CCL
// initialization is used; old module initialization order is not an ABI claim.
static ParamEditHandler gParamEditHandler;
// Default source vector is portable startup storage. Proofs must declare and
// seed the existing global vector capacity/delta domain explicitly, rather
// than claim the original module's uninspected static initializer recovered.
Core::Vector<Control::Timer *> Control::timers;

Control::Control(int tag)
    : lastLevel_(-1), parameter_(nullptr), altParameter_(nullptr),
      tertiaryParameter_(nullptr), io_(nullptr), tag_(tag) {}

Control::~Control() {
  for (int i = timers.count() - 1; i >= 0; --i) {
    Timer *value = timers.at(i);
    if (value->control == this) {
      timers.remove(value);
      delete value;
    }
  }
  if (parameter_)
    parameter_->removeObserver(this);
  if (altParameter_)
    altParameter_->removeObserver(this);
  if (tertiaryParameter_)
    tertiaryParameter_->removeObserver(this);
  parameter_ = nullptr;
}

void *Control::castTo(int type) { return type == 0x4374726c ? this : nullptr; }
void Control::paramChanged(Core::Portable::Parameter *parameter, int message) {
  if (message != Core::Portable::Parameter::kDestroyed)
    return;
  if (parameter_ == parameter)
    parameter_ = nullptr;
  else if (altParameter_ == parameter)
    altParameter_ = nullptr;
  else if (tertiaryParameter_ == parameter)
    tertiaryParameter_ = nullptr;
  parameter->removeObserver(this);
}
bool Control::setParameter(Core::Portable::Parameter *parameter, int) {
  if (parameter_ == parameter)
    return false;
  if (parameter_)
    parameter_->removeObserver(this);
  parameter_ = parameter;
  if (parameter_)
    parameter_->addObserver(this);
  if (parameter_)
    paramChanged(parameter_, Core::Portable::Parameter::kChanged);
  else
    broadcastValue(0);
  return true;
}
bool Control::setAltParameter(Core::Portable::Parameter *parameter) {
  if (altParameter_ == parameter)
    return false;
  if (altParameter_)
    altParameter_->removeObserver(this);
  altParameter_ = parameter;
  if (altParameter_)
    altParameter_->addObserver(this);
  if (altParameter_)
    paramChanged(altParameter_, Core::Portable::Parameter::kChanged);
  else if (parameter_)
    paramChanged(parameter_, Core::Portable::Parameter::kChanged);
  return true;
}
bool Control::setTertiaryParameter(Core::Portable::Parameter *parameter) {
  if (tertiaryParameter_ == parameter)
    return false;
  if (tertiaryParameter_)
    tertiaryParameter_->removeObserver(this);
  tertiaryParameter_ = parameter;
  if (tertiaryParameter_)
    tertiaryParameter_->addObserver(this);
  if (tertiaryParameter_)
    paramChanged(tertiaryParameter_, Core::Portable::Parameter::kChanged);
  else if (parameter_)
    paramChanged(parameter_, Core::Portable::Parameter::kChanged);
  return true;
}
int Control::getParameterMode() const { return 0; }
Core::Portable::Parameter *Control::getParameter() const { return parameter_; }
Core::Portable::Parameter *Control::getAltParameter() const {
  return altParameter_;
}
Core::Portable::Parameter *Control::getTertiaryParameter() const {
  return tertiaryParameter_;
}
void Control::setIO(IPanelIO *io) { io_ = io; }
void Control::broadcastValue(int) {}
void Control::transmit() {}
void Control::disableControl(bool, bool) {}
void Control::receiveValue(int) {}
void Control::timerCallback(int) {}
void Control::resendLastLevel() {
  if (lastLevel_ >= 0)
    transmit();
  else
    broadcastValue(0);
}

Control::Timer::Timer(Control *owner, int value, float seconds)
    : control(owner), tag(value) {
  const auto now = currentMilliseconds();
  // Original f32 multiply followed by truncation to signed64. The valid proof
  // domain excludes NaN/infinity/out-of-range conversion; no clamping added.
  const float milliseconds = seconds * 1000.f;
  deadline = wrapAdd(now, static_cast<std::int64_t>(milliseconds));
}
void Control::Timer::notify() { control->timerCallback(tag); }
void Control::startTimer(float seconds, int tag) {
  if (seconds <= 0.f)
    return;
  stopTimer(tag);
  Timer *value = new Timer(this, tag, seconds);
  if (timers.count() < timers.getCapacity() ||
      timers.resize(timers.count() + 1))
    timers.add(value);
  // The original does not free value when pointer-vector growth returns false.
}
void Control::stopTimer(int tag) {
  for (int i = 0; i < timers.count(); ++i) {
    Timer *value = timers.at(i);
    if (value->control == this && value->tag == tag) {
      timers.remove(value);
      delete value;
      return;
    }
  }
}
bool Control::isTimerRunning(int tag) {
  for (int i = 0; i < timers.count(); ++i) {
    const Timer *value = timers.at(i);
    if (value->control == this && value->tag == tag)
      return true;
  }
  return false;
}
void Control::onIdle() {
  gParamEditHandler.onIdle();
  const auto now = currentMilliseconds();
  Core::Vector<Timer *> due;
  for (int i = timers.count() - 1; i >= 0; --i) {
    Timer *value = timers.at(i);
    if (value->deadline <= now) {
      if (due.count() < due.getCapacity() || due.resize(due.count() + 1))
        due.add(value);
      timers.remove(value);
      // Failed temporary-vector growth still removes this timer, without
      // notifying/deleting it. Preserve the original orphaning behavior.
    }
  }
  const int count = due.count();
  for (int i = 0; i < count; ++i) {
    Timer *value = due.at(i);
    value->notify();
    delete value;
  }
}
} // namespace Presonus::Panel

namespace presonus::panel {
Presonus::Panel::ParamEditHandler &ControlAccess::paramEdits() {
  return Presonus::Panel::gParamEditHandler;
}
} // namespace presonus::panel
