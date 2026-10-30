#include "BiquadSine.hpp"
#include "IncrementalCore.hpp"
#include "presonus/dsp/biquad_calc.hpp"
#include <cmath>

namespace presonus::dsp::detail {
struct IncrementalHostMath {
  template <class T> T sin(T x) {
    if constexpr (std::is_same_v<T, float>)
      return biquadSourceSine(x);
    else
      return std::sin(x);
  }
  template <class T> T cos(T x) { return std::cos(x); }
  template <class T> T tan(T x) { return std::tan(x); }
  template <class T> T sqrt(T x) { return std::sqrt(x); }
  double pow(double x, double y) { return std::pow(x, y); }
};

template <class T> void calculateIncremental(BiquadState<T> &state) {
  IncrementalHostMath math;
  incrementalCoefficients(state, math);
}

inline int modeOrder(int mode) {
  switch (mode) {
  case 0:
  case 1:
  case 4:
  case 5:
    return 0;
  case 2:
  case 3:
  case 6:
  case 7:
  case 8:
  case 9:
  case 10:
  case 11:
  case 12:
    return 1;
  case 15:
  case 16:
    return 3;
  case 17:
  case 18:
  case 19:
  case 20:
  case 21:
    return 4;
  case 22:
  case 23:
  case 28:
  case 29:
    return 5;
  case 26:
  case 27:
    return 2;
  case 24:
  case 25:
  case 30:
  case 31:
    return 6;
  default:
    return -1;
  }
}

template <class T> T limitFrequency(T rate, float frequency) {
  const float lower = static_cast<float>(rate) * 0.0002f;
  return static_cast<T>(frequency < lower ? lower : frequency);
}
} // namespace presonus::dsp::detail

namespace DSP {
template <class T>
void BiquadCalc<T, false>::setParams(int mode, float frequency, float q,
                                     float gain) {
  const int previousMode = state_.mode;
  state_.mode = mode;
  state_.word54 = presonus::dsp::detail::modeOrder(mode);
  // The double instantiation narrows each old value before comparing to float
  // arguments. Individual double setters instead compare widened arguments.
  if (static_cast<float>(state_.frequency) != frequency) {
    state_.frequency =
        presonus::dsp::detail::limitFrequency(state_.rate, frequency);
    state_.dirty |= 1;
  }
  if (static_cast<float>(state_.q) != q) {
    state_.q = static_cast<T>(q);
    state_.dirty |= 2;
  }
  if (static_cast<float>(state_.gain) != gain) {
    state_.gain = static_cast<T>(gain);
    state_.dirty |= 4;
  }
  if (previousMode != mode)
    flush();
  else if (state_.dirty != 0)
    presonus::dsp::detail::calculateIncremental(state_);
}

template <> void BiquadCalc<double, false>::setQ(float value) {
  const double widened = value;
  if (state_.q == widened)
    return;
  state_.q = widened;
  state_.dirty |= 2;
  presonus::dsp::detail::calculateIncremental(state_);
}
template <> void BiquadCalc<double, false>::setGain(float value) {
  const double widened = value;
  if (state_.gain == widened)
    return;
  state_.gain = widened;
  state_.dirty |= 4;
  presonus::dsp::detail::calculateIncremental(state_);
}
template <> void BiquadCalc<double, false>::setFreq(float value) {
  const double widened = value;
  if (state_.frequency == widened)
    return;
  state_.frequency = presonus::dsp::detail::limitFrequency(state_.rate, value);
  state_.dirty |= 1;
  presonus::dsp::detail::calculateIncremental(state_);
}
template void BiquadCalc<float, false>::setParams(int, float, float, float);
template void BiquadCalc<double, false>::setParams(int, float, float, float);
} // namespace DSP
