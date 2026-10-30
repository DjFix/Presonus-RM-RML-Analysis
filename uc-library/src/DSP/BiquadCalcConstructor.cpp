#include "presonus/dsp/biquad_calc.hpp"

namespace DSP {
template <class T> BiquadCalc<T, false>::BiquadCalc() {
  // No aggregate/value initialization: preserve the original untouched bytes,
  // notably the sample-rate word(s), until setup supplies the actual rate.
  for (auto &smoother : state_.smoothers) {
    smoother.coefficient = 0x1.ff7ceep-1;
    smoother.previous = 0.;
    smoother.current = 0.;
  }
  state_.byte48 = 0;
  state_.dirty = 0;
  state_.mode = 6;
  state_.word54 = 1;
  state_.gain = T(0.);
  state_.frequency = T(1000.);
  state_.q = T(0x1.6666666666666p-1);
  state_.coefficients[0] = T(1.);
  for (unsigned i = 1; i < 5; ++i)
    state_.coefficients[i] = T(0.);
  state_.targets[0] = T(0.);
  state_.targets[1] = T(1000.);
  state_.targets[2] = T(0x1.6666666666666p-1);
  state_.piOverRate = T(0x1.2acb25eb05c70p-14);
  for (auto &value : state_.temporary)
    value = T(1.);
}

// Only double C1 exists in the selected original catalogue. Native C2 emitted
// by the compiler is not an invented original identity or readiness record.
template BiquadCalc<double, false>::BiquadCalc();
} // namespace DSP
