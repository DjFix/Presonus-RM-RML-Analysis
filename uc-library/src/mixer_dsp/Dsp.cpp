#include "presonus/mixer_dsp/Dsp.hpp"
#include <cstring>
#include <limits>

namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
std::uint32_t bits(float value) {
  std::uint32_t out;
  std::memcpy(&out, &value, 4);
  return out;
}
float value(std::uint32_t word) {
  float out;
  std::memcpy(&out, &word, 4);
  return out;
}
bool nan(std::uint32_t word) { return (word & 0x7fffffff) > 0x7f800000; }
bool inf(std::uint32_t word) { return (word & 0x7fffffff) == 0x7f800000; }
bool zero(std::uint32_t word) { return (word & 0x7fffffff) == 0; }
float quiet(std::uint32_t word) { return value(word | 0x00400000); }
float invalid(std::uint32_t sign_source) {
  return value((sign_source & 0x80000000) | 0x7fc00000);
}
// Force a binary32 rounding boundary for every original soft-float operation.
// This prevents contraction into host FMA from changing intermediate rounding.
// Original ARM libgcc NaN payload/sign rules differ from native SSE/NEON.
float add(float a, float b) {
  auto x = bits(a), y = bits(b);
  if (nan(x))
    return quiet(x);
  if (nan(y))
    return quiet(y);
  if (inf(x) && inf(y) && ((x ^ y) & 0x80000000))
    return invalid(x);
  volatile float r = a + b;
  return r;
}
float sub(float a, float b) { return add(a, value(bits(b) ^ 0x80000000)); }
float mul(float a, float b) {
  auto x = bits(a), y = bits(b);
  if (nan(x))
    return quiet(x);
  if (nan(y))
    return quiet(y);
  if (inf(x) && zero(y))
    return invalid(x);
  if (zero(x) && inf(y))
    return invalid(y);
  volatile float r = a * b;
  return r;
}
float div(float a, float b) {
  auto x = bits(a), y = bits(b);
  if (nan(x))
    return quiet(x);
  if (nan(y))
    return quiet(y);
  if (inf(x) && inf(y))
    return invalid(y);
  if (zero(x) && zero(y))
    return invalid(x);
  volatile float r = a / b;
  return r;
}
} // namespace

namespace Presonus::Dsp {
BilinearInterpolator::BilinearInterpolator()
    : Core::Interpolator(0.f, 1.f, 1.f, nullptr),
      state_{0.f, 1.f, 1.f, 0.f, .5f, 1.f, 1.f, 1.f, 1.f} {}
BilinearInterpolator::~BilinearInterpolator() = default;
float BilinearInterpolator::normalizedToRange(float value) const {
  const auto &s = state_;
  if (value < 0)
    value = 0;
  else if (!(value < 1))
    value = 1;
  if (value < s.normalizedMidpoint)
    return add(mul(value, s.lowSlope), s.minimum);
  return add(mul(sub(value, s.normalizedMidpoint), s.highSlope), s.midpoint);
}
float BilinearInterpolator::rangeToNormalized(float value) const {
  const auto &s = state_;
  if (s.minimum > value)
    value = s.minimum;
  else if (!(value < s.maximum))
    value = s.maximum;
  if (value < s.midpoint)
    return mul(sub(value, s.minimum), s.lowInverse);
  return add(mul(sub(value, s.midpoint), s.highInverse), s.normalizedMidpoint);
}
void BilinearInterpolator::setMidPoint(float rangeMidpoint,
                                       float normalizedMidpoint) {
  auto &s = state_;
  s.midpoint = !(s.minimum < rangeMidpoint) ? s.minimum
               : rangeMidpoint < s.maximum  ? rangeMidpoint
                                            : s.maximum;
  if (!(normalizedMidpoint < 1))
    normalizedMidpoint = 1;
  if (normalizedMidpoint > 0) {
    s.normalizedMidpoint = normalizedMidpoint;
    s.lowSlope = div(sub(rangeMidpoint, s.minimum), normalizedMidpoint);
  } else {
    s.normalizedMidpoint = 0;
    s.lowSlope = 1;
  }
  s.highSlope = s.normalizedMidpoint < 1 ? div(sub(s.maximum, rangeMidpoint),
                                               sub(1, s.normalizedMidpoint))
                                         : 1;
  s.lowInverse = div(1.f, s.lowSlope);
  s.highInverse = div(1.f, s.highSlope);
  Core::Interpolator::setRange(s.minimum, s.maximum, s.midpoint);
}
void BilinearInterpolator::setRange(float minimum, float maximum,
                                    float midpoint) {
  state_.minimum = minimum;
  state_.maximum = maximum;
  state_.midpoint = midpoint;
  setMidPoint(midpoint, state_.normalizedMidpoint);
}
float ShelbyGEQController::denormalizeValue(float value) {
  const float shifted = sub(value, .5f);
  return mul(add(shifted, shifted), 15);
}
int EQController::biquadFromBandType(EqType type) {
  static constexpr int table[] = {3, 8, 9, 6};
  return table[static_cast<unsigned>(type)];
}
} // namespace Presonus::Dsp
