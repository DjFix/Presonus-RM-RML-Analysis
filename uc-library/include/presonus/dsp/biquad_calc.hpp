#pragma once

#include <cstdint>
#include <cstring>

namespace presonus::dsp {
// Independent tagged source-port construction, not an original float C1.
struct BiquadSeedTag {};
// Independent portable storage model. Field spellings are not recovered
// original member declarations. Matching observed Linux offsets is a fixture
// convenience and does not establish original ARM object ABI.
template <class T> struct BiquadState {
  struct Smoother {
    double coefficient;
    double previous;
    double current;
  } smoothers[3];
  std::uint8_t byte48;
  std::uint8_t untouched49[3];
  std::uint32_t dirty;
  std::int32_t mode;
  std::int32_t word54;
  T rate; // Original double C1 does not initialize this member.
  T gain;
  T frequency;
  T q;
  T coefficients[5];
  T targets[3];
  T piOverRate;
  T temporary[13];
};
} // namespace presonus::dsp

namespace DSP {
template <class T, bool Option> class BiquadCalc;

template <class T> class BiquadCalc<T, false> {
public:
  BiquadCalc();
  BiquadCalc(presonus::dsp::BiquadSeedTag,
             const presonus::dsp::BiquadState<T> &seed) {
    std::memcpy(&state_, &seed, sizeof state_);
  }
  const presonus::dsp::BiquadState<T> &portableState() const { return state_; }

  // Parameter identities are encoded by the original symbols. The ordinary
  // return declarations are unresolved; void is a provisional source choice.
  // setup/flush are bounded source ports. Setters remain undefined until their
  // incremental dirty-dependent bodies are separately reconstructed.
  void setup(int, double);
  void flush();
  void setParams(int, float, float, float);
  void setQ(float);
  void setGain(float);
  void setFreq(float);

private:
  presonus::dsp::BiquadState<T> state_;
};
} // namespace DSP
