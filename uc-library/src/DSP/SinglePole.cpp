#include "presonus/dsp/single_pole.hpp"
#include <cmath>

#if defined(PRESONUS_DSP_GLIBC29_PRIVATE)
// Independent private source-provider binding for this candidate experiment.
// No host expf symbol is defined or replaced.
extern "C" float presonus_glibc29_expf(float);
#endif

namespace DSP {
// Portable float-return candidate: original non-template return declaration is
// unencoded. The local symbol name/parameters are preserved; native expf is an
// explicitly measured runtime dependency, not claimed equal to firmware 2.9.
[[gnu::noinline, gnu::used]] static float SinglePole(float frequency,
                                                     float sampleRate) {
  // Original literal bits c0c90fdb. Preserve all three binary32 roundings and
  // reciprocal-before-final-multiply order; no fused/reassociated expression.
  volatile float first = frequency * -0x1.921fb6p+2f;
  volatile float reciprocal = 1.0f / sampleRate;
  volatile float argument = first * reciprocal;
#if defined(PRESONUS_DSP_GLIBC29_PRIVATE)
  return presonus_glibc29_expf(argument);
#else
  return ::expf(argument);
#endif
}
} // namespace DSP

namespace presonus::dsp {
float singlePole(float frequency, float sampleRate) {
  return DSP::SinglePole(frequency, sampleRate);
}
} // namespace presonus::dsp
