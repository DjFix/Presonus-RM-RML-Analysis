#include "presonus/core/interpolator.hpp"
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

float floating(std::uint32_t bits) {
  float out;
  std::memcpy(&out, &bits, 4);
  return out;
}
std::uint32_t bits(float value) {
  std::uint32_t out;
  std::memcpy(&out, &value, 4);
  return out;
}
int main(int argc, char **argv) {
  try {
    if (std::fegetround() != FE_TONEAREST)
      throw std::runtime_error("requires FE_TONEAREST");
    volatile float normal = floating(0x00800000), half = .5f;
    volatile float subnormalOutput = normal * half;
    volatile float subnormal = floating(1), two = 2;
    volatile float subnormalInput = subnormal * two;
    if (bits(subnormalOutput) != 0x00400000 || bits(subnormalInput) != 2)
      throw std::runtime_error("requires gradual underflow; disable FTZ/DAZ");
    if (argc != 2)
      throw std::runtime_error("fixture path required");
    std::ifstream file(argv[1]);
    if (!file)
      throw std::runtime_error("fixture open failed");
    char op;
    std::uint32_t lo, hi, input, expected;
    std::map<char, unsigned> counts;
    while (file >> op >> std::hex >> lo >> hi >> input >> expected) {
      Core::LinearInterpolator forward;
      Core::LinearReverseInterpolator reverse;
      forward.portableRange() = {floating(lo), floating(hi)};
      reverse.portableRange() = forward.portableRange();
      std::uint32_t actual;
      switch (op) {
      case 'N':
        actual = bits(forward.normalizedToRange(floating(input)));
        break;
      case 'R':
        actual = bits(forward.rangeToNormalized(floating(input)));
        break;
      case 'V':
        actual = bits(reverse.normalizedToRange(floating(input)));
        break;
      case 'W':
        actual = bits(reverse.rangeToNormalized(floating(input)));
        break;
      default:
        throw std::runtime_error("unknown operation");
      }
      if (actual != expected) {
        std::cerr << op << ' ' << counts[op] << " lo=" << std::hex << lo
                  << " hi=" << hi << " input=" << input
                  << " expected=" << expected << " actual=" << actual << '\n';
        throw std::runtime_error("original ARM return-bit mismatch");
      }
      if (bits(forward.portableRange().minimum) != lo ||
          bits(forward.portableRange().maximum) != hi ||
          bits(reverse.portableRange().minimum) != lo ||
          bits(reverse.portableRange().maximum) != hi)
        throw std::runtime_error("portable state changed");
      ++counts[op];
    }
    if (!file.eof() || counts.size() != 4)
      throw std::runtime_error("incomplete fixtures");
    std::cout << "PASS:";
    for (const auto &[name, count] : counts)
      std::cout << ' ' << name << '=' << std::dec << count;
    std::cout << " exact original ARM return bits; state unchanged\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
