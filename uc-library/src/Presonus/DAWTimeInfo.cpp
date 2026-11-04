#include "presonus/DAWTimeInfo.hpp"

namespace Presonus {

unsigned int DAWTimeInfo::isMusicalDisplay() const {
  if (sourceState_)
    return static_cast<unsigned int>(sourceState_->musicalDisplay);
  return borrowedState_[0x134];
}

} // namespace Presonus

#include "core/portable/coreparams.h"
#include "presonus/DAWTimeInfo.hpp"
#include <stdexcept>

namespace Presonus {
DAWTimeInfo::State &DAWTimeInfo::mutableState() {
  if (!sourceState_)
    throw std::logic_error(
        "DAWTimeInfo source port requires explicit mutable State");
  return *sourceState_;
}
void DAWTimeInfo::updateTimeParam(Core::Portable::Parameter *parameter,
                                  const TimeString &time) {
  if (!parameter)
    return;
  auto &state = mutableState();
  parameter->fromString(state.musicalDisplay ? time.musicalText.data()
                                             : time.clockText.data(),
                        false);
}
void DAWTimeInfo::setMusicalDisplay(bool value) {
  auto &state = mutableState();
  if (state.musicalDisplay == value)
    return;
  state.musicalDisplay = value;
  for (unsigned i = 0; i < 3; ++i)
    updateTimeParam(state.parameters[i], state.times[i]);
}
void DAWTimeInfo::displayMilliSeconds(bool value) {
  auto &state = mutableState();
  if (state.milliSeconds == value)
    return;
  state.milliSeconds = value;
  for (unsigned i = 0; i < 3; ++i)
    updateTimeParam(state.parameters[i], state.times[i]);
}
DAWTimeInfo::Services &DAWTimeInfo::services() const {
  if (!sourceState_ || !sourceState_->services)
    throw std::logic_error(
        "DAWTimeInfo source port requires explicit Services");
  return *sourceState_->services;
}
void DAWTimeInfo::updateTimeContext(const UC::MessageAttributes &attributes) {
  auto &boundary = services();
  boundary.updateTempo(attributes);
  boundary.updateSignature(attributes);
}
void DAWTimeInfo::init(DAWClientComponent *client) {
  auto &state = mutableState();
  state.client = client;
  if (client)
    state.parameters = services().parameters(*client);
}
void DAWTimeInfo::locateTransport(const TimeString &time) {
  auto &state = mutableState();
  if (!state.client)
    return;
  services().locate(*state.client, time, state.musicalDisplay, state.locating);
  state.locating = true;
}
void DAWTimeInfo::locateTransportRelative(int delta) {
  auto &state = mutableState();
  if (!state.client)
    return;
  services().locateRelative(*state.client, delta, state.times[0],
                            state.musicalDisplay, state.locating);
  state.locating = true;
}
void DAWTimeInfo::parseTime(const UC::TimeCodeEvent &event,
                            TimeString &time) const {
  auto &boundary = services();
  for (unsigned i = 0; i < boundary.count(event); ++i) {
    auto item = boundary.item(event, i);
    bool clock = item.format == 0;
    auto &values = clock ? time.clockValues : time.musicalValues;
    unsigned digits = item.format == 1 ? 1 : 4;
    if (digits == 1)
      values[0] = item.values[0];
    else
      values = item.values;
    if (clock && !sourceState_->milliSeconds && digits == 4)
      digits = 3;
    boundary.print(clock ? time.clockText : time.musicalText, item, digits);
  }
}
void DAWTimeInfo::updateTime(const UC::TimeCodeEvent &event) {
  auto &state = mutableState();
  unsigned kind = services().eventKind(event), index;
  if (kind == 0)
    index = 0;
  else if (kind == 0x4c705374)
    index = 1;
  else if (kind == 0x4c70456e)
    index = 2;
  else
    return;
  parseTime(event, state.times[index]);
  updateTimeParam(state.parameters[index], state.times[index]);
  if (index == 0)
    state.locating = false;
}
void DAWTimeInfo::createTimeEvent(UC::TimeCodeEvent &event,
                                  const TimeString &time) {
  auto &state = mutableState();
  if (state.locating)
    return;
  auto &boundary = services();
  if (boundary.count(event) > 3)
    return;
  Services::Item item{state.musicalDisplay ? 2u : 0u, state.musicalDisplay
                                                          ? time.musicalValues
                                                          : time.clockValues};
  // Native payload stores the low 16 bits in each multi-field component.
  for (auto &value : item.values)
    value = static_cast<std::uint16_t>(value);
  boundary.append(event, item);
}
} // namespace Presonus
