#include "presonus/dsp/SLReverbController.hpp"
#include <bit>
#include <cmath>
#include <cstring>
#include <stdexcept>
namespace {
float f(std::uint32_t x) { return std::bit_cast<float>(x); }
std::uint32_t w(float x) { return std::bit_cast<std::uint32_t>(x); }
float mul(float a, float b) {
  volatile float v = a * b;
  return v;
}
float div(float a, float b) {
  volatile float v = a / b;
  return v;
}
float add(float a, float b) {
  volatile float v = a + b;
  return v;
}
float inverseGain(float gain) {
  return gain < f(3272605696U)
             ? f(1265751524U)
             : div(1.f, std::pow(10.f, mul(gain, f(1028443341U))));
}
} // namespace
namespace Presonus::Dsp {
SLReverbController::SLReverbController(presonus::dsp::ReverbPortState &s)
    : state_(s) {}
std::uint32_t SLReverbController::word(std::size_t offset) const {
  if (offset + 4 > state_.memory.size())
    throw std::out_of_range("reverb state");
  std::uint32_t x;
  std::memcpy(&x, state_.memory.data() + offset, 4);
  return x;
}
float SLReverbController::scalar(std::size_t o) const { return f(word(o)); }
void SLReverbController::store(std::size_t offset, std::uint32_t x) {
  if (offset + 4 > state_.memory.size())
    throw std::out_of_range("reverb state");
  std::memcpy(state_.memory.data() + offset, &x, 4);
}
std::uint32_t SLReverbController::presetWord(std::size_t offset) const {
  offset += static_cast<std::size_t>(word(0x2c)) * 216;
  if (offset + 4 > state_.presets.size())
    throw std::out_of_range("reverb preset");
  std::uint32_t x;
  std::memcpy(&x, state_.presets.data() + offset, 4);
  return x;
}
float SLReverbController::preset(std::size_t o) const {
  return f(presetWord(o));
}
void SLReverbController::dependency(std::uint32_t address,
                                    std::array<std::uint32_t, 4> a) {
  if (!state_.dependency)
    throw std::logic_error("unbound app DSP dependency");
  state_.dependency(address, a);
}
void SLReverbController::setDirty() {
  const int count = state_.valueCount();
  for (int i = 0; i < count; ++i)
    store(0x144 + 4U * i, w(-1.f));
  state_.memory[0x1c] = std::byte{1};
}
void SLReverbController::setReverbValue(int i, float value) {
  if (state_.valueCount() <= i)
    return;
  const auto offset =
      static_cast<std::size_t>((static_cast<std::uint32_t>(i) + 24U) * 4U);
  if (value != scalar(offset)) {
    store(offset, w(value));
    state_.memory[0x1c] = std::byte{1};
  }
}
float SLReverbController::getValue(int i) const {
  return state_.valueCount() > i
             ? scalar(static_cast<std::size_t>(
                   (static_cast<std::uint32_t>(i) + 24U) * 4U))
             : 0.f;
}
void SLReverbController::updateDiffusor() {
  const float rate = div(scalar(0x24), 1000.f);
  for (int i = 0; i < 4; ++i) {
    setReverbValue(i + 18, add(add(mul(rate, preset(52 + 4 * i)), 8.f), 1.f));
    setReverbValue(i + 22, f(presetWord(68 + 4 * i) + 0x80000000U));
  }
}
void SLReverbController::updateEarlyRefs() {
  const float rate = div(scalar(0x24), 1000.f);
  setReverbValue(9, mul(rate, scalar(0x34)));
  for (int i = 0; i < 4; ++i)
    setReverbValue(i + 26, mul(rate, preset(84 + 4 * i)));
}
void SLReverbController::coefficients(std::size_t offset, float gain,
                                      bool scale) {
  for (int i = 0; i < 5; ++i) {
    double value;
    std::memcpy(&value, state_.memory.data() + 0x338 + 8 * i, 8);
    float v = static_cast<float>(value);
    if (scale && (i % 2) == 0)
      v = mul(v, gain);
    store(offset + 4 * i, w(v));
  }
}
void SLReverbController::updateFilters() {
  constexpr int offsets[] = {20, 36, 120, 136, 152, 168};
  for (int i = 0; i < 6; ++i) {
    const auto o = offsets[i];
    const auto type = presetWord(o);
    const auto dest = 0x228 + 20 * i;
    if (type == 100) {
      for (int j = 0; j < 5; ++j)
        store(dest + 4 * j, j == 0 ? w(1.f) : 0);
    } else {
      dependency(0xbb514, {type == 200 ? 6 : type, presetWord(o + 4),
                           presetWord(o + 12), presetWord(o + 8)});
      coefficients(dest, type == 200 ? inverseGain(preset(o + 8)) : 1.f,
                   type == 200);
    }
    setReverbValue(i + 11, -1.f);
  }
}
void SLReverbController::updateDelayFilters() {
  if (static_cast<std::int32_t>(word(0x2c)) != 10)
    return;
  dependency(0xbb514, {6, word(0x54), word(0x5c), word(0x58)});
  coefficients(0x2a0, inverseGain(scalar(0x58)));
  setReverbValue(17, -1.f);
}
void SLReverbController::updateFDN() {
  const float base = preset(112), ratio = preset(116);
  float exponent =
      mul(div(mul(div(1.f, scalar(0x30)), base), 1000.f), f(3235712085U));
  setReverbValue(31, base);
  setReverbValue(32, ratio);
  float delay = div(mul(base, scalar(0x24)), 1000.f),
        decay = std::exp(exponent);
  for (int i = 0; i < 4; ++i) {
    setReverbValue(i + 38, delay);
    delay = mul(delay, ratio);
    setReverbValue(i + 33, decay);
    exponent = mul(exponent, ratio);
    decay = std::exp(exponent);
  }
  setReverbValue(37, preset(108));
  for (int i = 0; i < 4; ++i) {
    const float p = preset(184 + 4 * i);
    setReverbValue(42 + i, p == 0.f ? 0.f : div(f(981668463U), p));
    setReverbValue(46 + i, static_cast<float>(static_cast<std::int32_t>(
                               presetWord(200 + 4 * i))));
  }
}
void SLReverbController::calcParams(int id) {
  const auto mode = static_cast<std::int32_t>(word(0x2c));
  switch (id) {
  case 1:
    if (mode > 8) {
      updateDelayFilters();
      return;
    }
    updateDiffusor();
    updateEarlyRefs();
    updateFDN();
    updateFilters();
    setReverbValue(9, div(mul(scalar(0x24), scalar(0x34)), 1000.f));
    break;
  case 2:
    if (mode <= 8)
      updateFDN();
    else
      setReverbValue(50, div(mul(scalar(0x3c), scalar(0x24)), 1000.f));
    return;
  case 3:
    if (mode <= 8)
      setReverbValue(9, div(mul(scalar(0x24), scalar(0x34)), 1000.f));
    else
      setReverbValue(51, scalar(0x40));
    return;
  case 4:
    if (mode == 9 || mode == 10) {
      setReverbValue(53, scalar(0x48));
      return;
    }
    if (mode == 11 || mode == 12) {
      setReverbValue(52, scalar(0x44));
      return;
    }
    break;
  case 5:
    if (mode == 10)
      updateDelayFilters();
    else if (mode == 11 || mode == 12)
      setReverbValue(53, scalar(0x48));
    return;
  case 6:
    if (mode == 10)
      updateDelayFilters();
    else if (mode == 11)
      setReverbValue(54, scalar(0x4c));
    else if (mode == 12)
      setReverbValue(55, scalar(0x50));
    return;
  case 7:
    if (mode == 10)
      updateDelayFilters();
    else if (mode == 11)
      setReverbValue(55, scalar(0x50));
    return;
  default:
    return;
  }
  const float gain = scalar(0x38);
  setReverbValue(30, gain < f(3272605696U)
                         ? f(864517951U)
                         : std::pow(10.f, mul(gain, f(1028443341U))));
}
void SLReverbController::setupProcess(const SetupProperty &property) {
  // Observed input accesses only. This does not define SetupProperty's layout.
  std::uint32_t rate, block;
  const auto *bytes = reinterpret_cast<const std::byte *>(&property);
  std::memcpy(&rate, bytes + 8, 4);
  std::memcpy(&block, bytes + 12, 4);
  if (scalar(0x24) == f(rate) && word(0x28) == block)
    return;
  store(0x24, rate);
  store(0x28, block);
  const auto wide = std::bit_cast<std::uint64_t>(static_cast<double>(f(rate)));
  dependency(0xbb3e0, {block, static_cast<std::uint32_t>(wide),
                       static_cast<std::uint32_t>(wide >> 32)});
  dependency(0xbf5c0, {1060320051U, 0, 0});
  dependency(0xc1338, {0, 0, 0});
  dependency(0xc30d8, {1148846080U, 0, 0});
  calcParams(1);
  if (static_cast<std::int32_t>(word(0x2c)) > 8)
    calcParams(2);
  setDirty();
}
} // namespace Presonus::Dsp
