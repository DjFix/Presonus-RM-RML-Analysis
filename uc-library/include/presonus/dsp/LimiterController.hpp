#pragma once

#include "presonus/dsp/Controller.hpp"

namespace presonus::dsp {
// Independent source-port state for the four observed limiter words.
struct LimiterControllerState {
  std::uint32_t enabled = 0;
  float thresholdAmplitude = 0x1.5561aap+0f;
  float smoothing = 0.f;
  float reductionAmplitude = 1.f;
};
} // namespace presonus::dsp

namespace Presonus::Dsp {
// The original RTTI identifies Controller as the base. The host class and
// its ordinary return contracts do not establish the original ARM ABI.
class LimiterController : public Controller {
public:
  explicit LimiterController(int id);
  ~LimiterController() override;

  float getValue(int tag) const override;
  float setValue(int tag, float value) override;
  void doUpdates() override;

  presonus::dsp::LimiterControllerState &portableLimiterState() {
    return limiter_;
  }

private:
  presonus::dsp::LimiterControllerState limiter_;
};
} // namespace Presonus::Dsp
