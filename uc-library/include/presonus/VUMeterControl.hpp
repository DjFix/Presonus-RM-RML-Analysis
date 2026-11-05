#pragma once
#include "core/public/corevector.h"
#include "presonus/PotControl.hpp"
#include "presonus/delay_timer.hpp"
namespace Presonus {
// Portable source state. Native field offsets and original ABI are not claimed.
class VUMeterControl : public PotControl {
public:
  explicit VUMeterControl(const Core::TRect<int> &size);
  ~VUMeterControl() override;
  void setFrame(int frame) override;
  void setAttributes(const Core::Portable::Attributes &attributes) override;
  void onIdle() override;
  int portableThresholdCount() const { return thresholds_.count(); }
  float portableThreshold(int index) const { return thresholds_[index]; }
  void changeFrames() override;
  void portableBindThresholds(const float *values, int count) {
    thresholds_.empty();
    for (int i = 0; i < count; ++i)
      thresholds_.add(values[i]);
  }
  // Independent source-port observation and binding API.
  void portableBindFrameState(int frame, int count, int flags, bool dirty) {
    previousValue_ = frame;
    frameCount_ = count;
    options = flags;
    dirty_ = dirty;
  }
  bool portableDirty() const { return dirty_; }
  void portableBindTimer(const presonus::timing::DelayTimerState &state) {
    presonus::timing::DelayTimerAccess::set(timer_, state);
  }
  presonus::timing::DelayTimerState portableTimer() const {
    return presonus::timing::DelayTimerAccess::get(timer_);
  }

private:
  Core::Vector<float> thresholds_;
  bool dirty_ = false;
  DelayTimer timer_;
};
} // namespace Presonus
