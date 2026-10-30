#include "presonus/dsp/biquad_calc.hpp"

#include "BiquadSine.hpp"
#include "CalculationCore.hpp"
#include <cmath>

namespace presonus::dsp::detail {
struct MeasuredHostMath {
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
} // namespace presonus::dsp::detail

namespace DSP {
template <class T> void BiquadCalc<T, false>::flush() {
  presonus::dsp::detail::MeasuredHostMath math;
  presonus::dsp::detail::flushCoefficients(state_, math);
}

template <class T> void BiquadCalc<T, false>::setup(int, double sampleRate) {
  state_.rate = static_cast<T>(sampleRate);
  state_.piOverRate = T(0x1.921fb54442d18p+1) / state_.rate;

  // Original literal bits 3f689374c0000000 are the widened binary32
  // approximation of .003, not the nearest binary64 encoding of .003.
  // Both roles calculate this count from the incoming DOUBLE sample rate.
  const double rounded = (sampleRate * 0x1.89374cp-9) * 0x1p-5 + 0x1p-1;
  const int count = static_cast<int>(rounded);
  if (count > 0) {
    const double reciprocal = 1.0 / static_cast<double>(count);
    for (auto &smoother : state_.smoothers)
      smoother.coefficient = std::pow(0.5, reciprocal);
  } else {
    for (auto &smoother : state_.smoothers)
      smoother.coefficient = 0.;
  }
  flush();
}

template void BiquadCalc<float, false>::flush();
template void BiquadCalc<double, false>::flush();
template void BiquadCalc<float, false>::setup(int, double);
template void BiquadCalc<double, false>::setup(int, double);
} // namespace DSP
