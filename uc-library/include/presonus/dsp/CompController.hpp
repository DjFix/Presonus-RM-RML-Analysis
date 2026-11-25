#pragma once
#include "presonus/dsp/Controller.hpp"
#include <array>

namespace Presonus::Dsp {

// Portable class using the recovered base interface. Ordinary return
// declarations and the original ARM object layout remain unresolved.
class CompController : public Controller {
public:
  explicit CompController(int);
  ~CompController() override;
  float getValue(int) const override;
  float setValue(int, float) override;
  void doUpdates() override;

private:
  float thresholdLog_ = 0.f;
  float release_ = .2f;
  float attack_ = .01f;
  float inverseRatio_ = .25f;
  bool softKnee_ = false;
  std::array<float, 64> table_{};
  float tableThreshold_ = 0.f;
  float gain_ = 0.f;
  float inverseStep_ = 0.f;
  float releaseCoefficient_ = 0.f;
  float attackCoefficient_ = 0.f;
  float envelopeCoefficient_ = 0.f;
  float detectorCoefficient_ = 0.f;
  float lowerKnee_ = 0.f;
  bool enabled_ = false;
  float reduction_ = 1.f;
  bool automatic_ = false;
};

} // namespace Presonus::Dsp
