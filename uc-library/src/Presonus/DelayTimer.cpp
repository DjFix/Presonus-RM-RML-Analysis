#include "presonus/delay_timer.hpp"
#include "presonus/dice/packet_services.hpp"
#include <cstring>

namespace Presonus {
DelayTimer::DelayTimer(float seconds)
    : start_(0), duration_(0), elapsed_(0), reciprocal_(0), executing_(false) {
  const float milliseconds = seconds * 1000.0f;
  // Defined port domain: finite multiplied value representable by int64_t.
  duration_ = static_cast<std::int64_t>(milliseconds);
  if (seconds > 0.0f)
    reciprocal_ = 1.0f / milliseconds;
}
DelayTimer::~DelayTimer() = default;

void DelayTimer::reset() {
  elapsed_ = 0;
  executing_ = false;
}
void DelayTimer::beginAction(float seconds) {
  executing_ = true;
  if (seconds > 0.0f) {
    const float milliseconds = seconds * 1000.0f;
    duration_ = static_cast<std::int64_t>(milliseconds);
    reciprocal_ = 1.0f / milliseconds;
  }
  elapsed_ = 0;
  start_ = presonus::dice::packetClockRawTicks() / 1000000;
}
bool DelayTimer::endAction() {
  if (!executing_)
    return false;
  elapsed_ = getElapsedMilliseconds();
  executing_ = false;
  return elapsed_ >= duration_;
}
bool DelayTimer::wasLongEnough() const {
  return !executing_ && elapsed_ >= duration_;
}
bool DelayTimer::isExecuting() const { return executing_; }
bool DelayTimer::isLongEnoughYet() const {
  return (executing_ ? getElapsedMilliseconds() : elapsed_) >= duration_;
}
float DelayTimer::getProgressNormalized() const {
  return executing_ ? static_cast<float>(getElapsedMilliseconds()) * reciprocal_
                    : -1.0f;
}
std::int64_t DelayTimer::getElapsedMilliseconds() const {
  // The original SUBS/SBC wraps the two-word signed result. Preserve its bits
  // explicitly; do not introduce signed C++ overflow or clamp backward clocks.
  const std::uint64_t result =
      static_cast<std::uint64_t>(presonus::dice::packetClockRawTicks() /
                                 1000000) -
      static_cast<std::uint64_t>(start_);
  std::int64_t value;
  std::memcpy(&value, &result, sizeof(value));
  return value;
}
} // namespace Presonus
