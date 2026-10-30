#include "presonus/mixer_dsp/FaderCurveInterpolator.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

namespace {
float floating(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, sizeof(value));
  return value;
}
std::uint32_t bits(float value) {
  std::uint32_t word;
  std::memcpy(&word, &value, sizeof(word));
  return word;
}
} // namespace

int main() {
  unsigned operation;
  int count;
  std::uint32_t input;
  while (std::cin >> operation >> count >> input) {
    if (count < 2 || count > 64 || operation > 5)
      return 2;
    std::vector<Core::SegmentInterpolator::BreakPoint> points;
    for (int i = 0; i < count; ++i) {
      std::uint32_t normalized, range;
      if (!(std::cin >> normalized >> range))
        return 3;
      points.push_back({floating(normalized), floating(range)});
    }
    Core::SegmentInterpolator base(count, points.data());
    Presonus::Dsp::FaderCurveInterpolator candidate(count, points.data());
    const float value = floating(input);
    float result = 0.f;
    switch (operation) {
    case 0:
      result = base.normalizedToRange(value);
      break;
    case 1:
      result = base.rangeToNormalized(value);
      break;
    case 2:
      result = candidate.normalizedToDb(value);
      break;
    case 3:
      result = candidate.dbToNormalized(value);
      break;
    case 4:
      result = candidate.normalizedToRange(value);
      break;
    case 5:
      result = candidate.rangeToNormalized(value);
      break;
    }
    std::cout << bits(result) << std::endl;
  }
}
