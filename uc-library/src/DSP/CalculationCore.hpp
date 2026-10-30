#pragma once

#include "presonus/dsp/biquad_calc.hpp"
#include <type_traits>

namespace presonus::dsp::detail {
// Shared typed coefficient equations, bound by DSP::BiquadCalc::flush.
// Current host math is measured only over the explicitly retained corpus.
template <class T, class Math>
bool flushCoefficients(BiquadState<T> &s, Math &math) {
  static_assert(std::is_same_v<T, float> || std::is_same_v<T, double>);
  const auto mode = static_cast<std::uint32_t>(s.mode);

  const T gain = s.gain;
  const T frequency = s.frequency;
  const T q = s.q;
  const T values[] = {gain, frequency, q};
  for (unsigned i = 0; i < 3; ++i) {
    s.targets[i] = values[i];
    s.smoothers[i].previous = static_cast<double>(values[i]);
    s.smoothers[i].current = static_cast<double>(values[i]);
  }
  s.dirty = 7;
  T *c = s.coefficients;
  T *t = s.temporary;
  switch (mode) {
  case 0: {
    t[0] = math.tan(frequency * s.piOverRate);
    const T k = t[0];
    t[5] = T(1) / (k + T(1));
    const T norm = t[5];
    c[1] = norm * (T(1) - k);
    c[3] = T(0);
    c[4] = T(0);
    const T value = k * norm;
    c[2] = value;
    c[0] = value;
    break;
  }
  case 1: {
    t[0] = math.tan(frequency * s.piOverRate);
    const T k = t[0];
    t[5] = T(1) / (k + T(1));
    const T norm = t[5];
    c[1] = norm * (T(1) - k);
    c[0] = norm;
    c[2] = -norm;
    c[4] = T(0);
    c[3] = T(0);
    break;
  }
  case 2:
  case 3: {
    t[0] = math.tan(frequency * s.piOverRate);
    const T k = t[0];
    const T squared = k * k;
    t[4] = squared;
    const T ratio = k / q;
    t[3] = (squared + ratio) + T(1);
    const T norm = T(1) / t[3];
    const T difference = T(1) - squared;
    c[1] = norm * (difference + difference);
    c[3] = norm * ((ratio - T(1)) - squared);
    if (mode == 2) {
      const T value = norm * squared;
      c[0] = value;
      c[2] = value + value;
      c[4] = value;
    } else {
      c[0] = norm;
      c[4] = norm;
      c[2] = norm * T(-2);
    }
    break;
  }
  case 4:
  case 5:
  case 15:
  case 16: {
    const T controlGain =
        mode == 15 || mode == 16 ? gain * T(0x1.5555555555555p-2) : gain;
    const T exponent = controlGain * T(0.05);
    t[2] = static_cast<T>(math.pow(10., static_cast<double>(exponent)));
    const T amplitude = t[2];
    const T angle = s.piOverRate * s.targets[1];
    if (mode == 4 || mode == 15) {
      // The original <= comparison includes amplitude==1 in this branch.
      if (amplitude <= T(1)) {
        t[0] = T(1) / math.tan(angle);
        t[5] = T(1) / (t[0] + T(1));
        t[3] = T(1) / math.tan(amplitude * angle);
      } else {
        t[3] = T(1) / math.tan(angle);
        t[0] = T(1) / math.tan(angle / amplitude);
        t[5] = T(1) / (t[0] + T(1));
      }
      c[1] = (t[0] - T(1)) * t[5];
      c[3] = T(0);
      c[0] = ((t[3] + T(1)) * amplitude) * t[5];
      c[2] = ((T(1) - t[3]) * amplitude) * t[5];
      c[4] = T(0);
    } else {
      const T pi = T(0x1.921fb54442d18p+1);
      const T cutoff = T(0x1.fef9db22d0e56p-2);
      // These are actual per-width literal words, not recomputed values.
      const T clippedK = [] {
        if constexpr (std::is_same_v<T, float>)
          return T(0x1.9bc2e2p-9f);
        else
          return T(0x1.9bc6b430a5779p-9);
      }();
      const T clippedNorm = [] {
        if constexpr (std::is_same_v<T, float>)
          return T(0x1.fe6586p-1f);
        else
          return T(0x1.fe65836e1d196p-1);
      }();
      if (amplitude >= T(1)) {
        const T ratio = (amplitude * s.targets[1]) / s.rate;
        if (ratio < cutoff) {
          t[0] = T(1) / math.tan(ratio * pi);
          t[5] = T(1) / (t[0] + T(1));
        } else {
          t[0] = clippedK;
          t[5] = clippedNorm;
        }
        t[3] = T(1) / math.tan(angle);
      } else {
        t[0] = T(1) / math.tan(angle);
        t[5] = T(1) / (t[0] + T(1));
        const T ratio = (s.targets[1] / s.rate) / amplitude;
        t[3] = ratio < cutoff ? T(1) / math.tan(ratio * pi) : clippedK;
      }
      c[1] = (t[0] - T(1)) * t[5];
      c[3] = T(0);
      c[0] = (t[3] + T(1)) * t[5];
      c[2] = (T(1) - t[3]) * t[5];
      c[4] = T(0);
    }
    break;
  }
  case 6: {
    const T exponent = gain * T(0.05);
    t[2] = static_cast<T>(math.pow(10., static_cast<double>(exponent)));
    // Original flush sets dirty7; preserve the actual dirty branch in the
    // shared core because future entry prefixes do not always recompute K.
    if (s.dirty & 1) {
      t[0] = math.tan(s.piOverRate * s.targets[1]);
      t[4] = t[0] * t[0];
    }
    const T root = math.sqrt(t[2]);
    const T product = t[0] * root;
    t[1] = product / s.targets[2];
    const T ratio = t[1] / t[2];
    t[3] = (ratio + t[4]) + T(1);
    const T norm = T(1) / t[3];
    const T difference = T(1) - t[4];
    c[1] = norm * (difference + difference);
    c[3] = norm * ((ratio - T(1)) - t[4]);
    c[0] = norm * ((t[4] + t[1]) + T(1));
    const T negativeDifference = t[4] - T(1);
    c[2] = norm * (negativeDifference + negativeDifference);
    c[4] = norm * ((t[4] - t[1]) + T(1));
    break;
  }
  case 7:
  case 8:
  case 9:
  case 10:
  case 11:
  case 12:
  case 17:
  case 18:
  case 19:
  case 20:
  case 21:
  case 22:
  case 23:
  case 24:
  case 25:
  case 28:
  case 29:
  case 30:
  case 31: {
    t[6] = (frequency + frequency) * s.piOverRate;
    t[7] = math.sin(t[6]);
    t[8] = math.cos(t[6]);
    t[9] = t[7] / (q + q);
    if (mode == 11) {
      const T width = (t[7] * s.targets[2]) / t[6];
      t[9] = t[7] / (width + width);
      const T exponent = s.targets[0] * T(0.025);
      t[10] = static_cast<T>(math.pow(10., static_cast<double>(exponent)));
      const T amplitude = t[10];
      const T alpha = t[9];
      t[12] = amplitude / (amplitude + alpha);
      const T norm = t[12];
      c[1] = norm * (t[8] + t[8]);
      c[3] = -(T(1) - alpha / amplitude) * norm;
      const T product = alpha * amplitude;
      c[0] = (product + T(1)) * norm;
      c[2] = -c[1];
      c[4] = (T(1) - product) * norm;
      break;
    }
    if (mode == 8 || mode == 9 || mode == 17 || mode == 18 || mode >= 28) {
      T controlGain = s.targets[0];
      if (mode == 17 || mode == 18)
        controlGain = controlGain * T(0.5);
      else if (mode == 28 || mode == 29)
        controlGain = controlGain * T(0x1.5555555555555p-2);
      else if (mode == 30 || mode == 31)
        controlGain = controlGain * T(0.25);
      const T exponent = controlGain * T(0.025);
      t[10] = static_cast<T>(math.pow(10., static_cast<double>(exponent)));
      t[11] = math.sqrt(t[10]) / s.targets[2];
      const T amplitude = t[10];
      const T minus = amplitude - T(1);
      const T plus = amplitude + T(1);
      const T minusCos = minus * t[8];
      const T plusCos = plus * t[8];
      const T beta = t[11] * t[7];
      const bool high = mode == 9 || mode == 18 || mode == 29 || mode == 31;
      if (high) {
        const T difference = plus - minusCos;
        t[12] = T(1) / (beta + difference);
        const T norm = t[12];
        const T scaled = norm * amplitude;
        c[1] = norm * ((minus - plusCos) * T(-2));
        c[3] = -(difference - beta) * norm;
        const T sum = plus + minusCos;
        c[0] = (beta + sum) * scaled;
        c[2] = ((minus + plusCos) * T(-2)) * scaled;
        c[4] = (sum - beta) * scaled;
      } else {
        const T sum = plus + minusCos;
        t[12] = T(1) / (beta + sum);
        const T norm = t[12];
        const T scaled = norm * amplitude;
        const T feedback = minus + plusCos;
        c[1] = norm * (feedback + feedback);
        c[3] = -(sum - beta) * norm;
        const T difference = plus - minusCos;
        c[0] = (beta + difference) * scaled;
        const T middle = minus - plusCos;
        c[2] = (middle + middle) * scaled;
        c[4] = (difference - beta) * scaled;
      }
      break;
    }
    t[12] = T(1) / (t[9] + T(1));
    const T cosine = t[8];
    const T alpha = t[9];
    const T norm = t[12];
    c[1] = (cosine + cosine) * norm;
    if (mode == 12)
      c[3] = -(T(1) - alpha) * norm;
    else
      c[3] = (alpha - T(1)) * norm;
    if (mode == 7 || mode == 21) {
      c[0] = alpha * norm;
      c[2] = T(0);
      c[4] = -c[0];
    } else if (mode == 10) {
      c[0] = (T(1) - alpha) * norm;
      c[2] = -c[1];
      c[4] = T(1);
    } else if (mode == 12) {
      c[0] = norm;
      c[2] = -c[1];
      c[4] = norm;
    } else if (mode == 19 || mode == 22 || mode == 24) {
      const T difference = T(1) - cosine;
      c[0] = (difference * T(0.5)) * norm;
      c[2] = difference * norm;
      c[4] = c[0];
    } else {
      const T sum = cosine + T(1);
      c[0] = (sum * T(0.5)) * norm;
      c[2] = -sum * norm;
      c[4] = c[0];
    }
    break;
  }
  case 26:
  case 27: {
    // The two original role tables enter distinct first-order branches.
    // Retain reciprocal placement and the per-instantiation pi literal.
    const T ratio = frequency / s.rate;
    const T complement = T(0.5) - ratio;
    const T pi = T(0x1.921fb54442d18p+1);
    t[3] = math.tan(complement * pi);
    const T k = t[3];
    t[12] = T(1) / (k + T(1));
    const T norm = t[12];
    c[1] = norm * (k - T(1));
    c[3] = T(0);
    c[4] = T(0);
    if (mode == 26) {
      c[0] = k * norm;
      c[2] = -k * norm;
    } else {
      c[0] = norm;
      c[2] = norm;
    }
    break;
  }
  default:
    c[4] = T(0);
    c[0] = T(1);
    c[1] = T(0);
    c[2] = T(0);
    c[3] = T(0);
    break;
  }
  s.dirty = 0;
  s.targets[1] = frequency;
  return true;
}
} // namespace presonus::dsp::detail
