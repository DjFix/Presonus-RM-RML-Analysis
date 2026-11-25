#pragma once

#include "presonus/dsp/Controller.hpp"
#include "presonus/dsp/biquad_calc.hpp"

#include <array>

namespace presonus::dsp {
// Portable representation of observable control and property state.
struct GateControllerSourceState {
  std::array<float, 5> coefficients{};
  float range = 0.f, inverseThreshold = 10000.f;
  float attack = .01f, release = .25f;
  float attackSmoothing = 0.f, releaseSmoothing = 0.f;
  int releaseSamples = 0;
  int enabled = 0, expander = 0, keyListen = 0;
  int filterMode = 7;
  float filterFrequency = 1200.f, filterQ = 8.f, filterGain = 1.f;
  float reduction = 1.f;
};
} // namespace presonus::dsp

namespace Presonus::Dsp {
class GateController : public Controller {
public:
  // Register the EQ, Compressor and Gate source providers before first use.
  explicit GateController(int);
  ~GateController() override;

  // Provisional source interfaces. The ordinary native return types are
  // unresolved.
  float getValue(int) const override;
  float setValue(int, float) override;
  void setupProcess(const SetupProperty &) override;
  // The base flush path calls this only after positive-rate setup.
  void doUpdates() override;

  presonus::dsp::GateControllerSourceState &gateSourceState() noexcept {
    return gate_;
  }
  const presonus::dsp::BiquadState<double> &filterSourceState() const noexcept {
    return filter_.portableState();
  }

private:
  presonus::dsp::GateControllerSourceState gate_;
  DSP::BiquadCalc<double, false> filter_;
};
} // namespace Presonus::Dsp
