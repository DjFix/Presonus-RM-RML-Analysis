#pragma once
#include <cstdint>

namespace presonus::timing {
struct DelayTimerAccess;
struct DelayTimerState {
  std::int64_t start, duration, elapsed;
  float reciprocal;
  bool executing;
};
} // namespace presonus::timing
namespace Presonus {
// Shared original class and parameter/const identities. Storage is portable;
// ordinary return spellings remain declaration-pending, not ARM ABI claims.
class DelayTimer {
public:
  explicit DelayTimer(float);
  ~DelayTimer(); // Original D1/D2 only: no original D0/virtual slot exists.
  void reset();
  void beginAction(float);
  bool endAction();
  bool wasLongEnough() const;
  bool isExecuting() const;
  bool isLongEnoughYet() const;
  float getProgressNormalized() const;
  std::int64_t getElapsedMilliseconds() const;

private:
  std::int64_t start_, duration_, elapsed_;
  float reciprocal_;
  bool executing_;
  friend struct presonus::timing::DelayTimerAccess;
};
} // namespace Presonus
namespace presonus::timing {
// Independent semantic fixture access; never reads native padding/ended life.
struct DelayTimerAccess {
  static void set(Presonus::DelayTimer &timer, const DelayTimerState &state) {
    timer.start_ = state.start;
    timer.duration_ = state.duration;
    timer.elapsed_ = state.elapsed;
    timer.reciprocal_ = state.reciprocal;
    timer.executing_ = state.executing;
  }
  static DelayTimerState get(const Presonus::DelayTimer &timer) {
    return {timer.start_, timer.duration_, timer.elapsed_, timer.reciprocal_,
            timer.executing_};
  }
};
} // namespace presonus::timing
