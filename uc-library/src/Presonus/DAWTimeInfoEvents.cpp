#include "presonus/DAWTimeInfo.hpp"
#include "presonus/IDAWTimeInfo.hpp"
#include "presonus/surface/TransportHandler.hpp"
#include "presonus/uc/misc_events.hpp"
#include <cstring>
#include <stdexcept>

namespace {
// ARM addition wraps at 32 bits; signed overflow is not delegated to host C++.
std::int32_t add(std::int32_t a, std::int32_t b) {
  std::uint32_t bits = std::uint32_t(a) + std::uint32_t(b);
  std::int32_t result;
  std::memcpy(&result, &bits, 4);
  return result;
}
std::int32_t numerator(const std::uint8_t *record) {
  std::uint32_t bits = 0;
  for (unsigned i = 0; i < 4; ++i)
    bits |= std::uint32_t(record[8 + i]) << (8 * i);
  std::int32_t result;
  std::memcpy(&result, &bits, 4);
  return result;
}
} // namespace
namespace Presonus {
const DAWTimeInfo::TimeString *DAWTimeInfo::getTransportTime() const {
  if (sourceState_)
    return &sourceState_->times[0];
  return reinterpret_cast<const TimeString *>(borrowedState_ + 12);
}
const DAWTimeInfo::TimeString *DAWTimeInfo::getLoopStartTime() const {
  if (sourceState_)
    return &sourceState_->times[1];
  return reinterpret_cast<const TimeString *>(borrowedState_ + 112);
}
void DAWTimeInfo::createDeltaTimeEvent(UC::TimeCodeEvent &event, int delta,
                                       const TimeString &time) {
  if (!sourceState_)
    throw std::logic_error("createDeltaTimeEvent requires source-port state");
  auto &state = *sourceState_;
  if (state.locating)
    return;
  auto values = state.musicalDisplay ? time.musicalValues : time.clockValues;
  unsigned format = 0;
  if (state.musicalDisplay) {
    values[1] = add(values[1], delta);
    values[2] = 1;
    values[3] = 0;
    format = 2;
    if (values[1] > 0) {
      if (!state.signatureMap)
        throw std::logic_error("musical delta requires signature map");
      int n = numerator(state.signatureMap->findItemByBar(add(values[0], -1)));
      if (n < values[1]) {
        values[1] = add(add(values[1], ~n), 1);
        values[0] = add(values[0], 1);
      }
    } else if (add(values[0], -2) < 0) {
      values[0] = 0;
      values[1] = 0;
    } else {
      if (!state.signatureMap)
        throw std::logic_error("musical delta requires signature map");
      int n = numerator(state.signatureMap->findItemByBar(add(values[0], -2)));
      values[1] = n;
      values[0] = add(values[0], -1);
    }
  } else {
    values[2] = add(values[2], delta);
    if (values[2] > 59) {
      values[2] = add(values[2], -60);
      values[1] = add(values[1], 1);
      if (values[1] > 59) {
        values[1] = add(values[1], -60);
        values[0] = add(values[0], 1);
      }
    } else if (values[2] < 0) {
      values[2] = add(values[2], 60);
      values[1] = add(values[1], -1);
      if (values[1] < 0) {
        values[1] = add(values[1], 60);
        values[0] = add(values[0], -1);
        if (values[0] < 0)
          values[0] = values[1] = values[2] = 0;
      }
    }
    values[3] = 0;
  }
  // Actual existing portable event storage; no host object byte offsets.
  // Capacity is checked after time/map computation, matching original order.
  if (event.recordCount > 3)
    return;
  auto &record = event.records[event.recordCount];
  record.a = static_cast<unsigned char>(format);
  record.b = 1;
  for (unsigned i = 0; i < 4; ++i) {
    const auto value = static_cast<std::uint16_t>(values[i]);
    record.rawBytes[2 * i] = static_cast<unsigned char>(value);
    record.rawBytes[2 * i + 1] = static_cast<unsigned char>(value >> 8);
  }
  ++event.recordCount;
}
} // namespace Presonus
