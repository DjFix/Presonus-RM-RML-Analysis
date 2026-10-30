#include "presonus/mixer_dsp/Dsp.hpp"
#include <array>
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>

using namespace Presonus::Dsp;
std::array<unsigned char, 36> unhex(const std::string &text) {
  if (text.size() != 72)
    throw std::runtime_error("state width");
  std::array<unsigned char, 36> out{};
  for (unsigned i = 0; i < 36; ++i)
    out[i] = static_cast<unsigned char>(
        std::stoul(text.substr(i * 2, 2), nullptr, 16));
  return out;
}
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
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (std::fegetround() != FE_TONEAREST)
      throw std::runtime_error("requires FE_TONEAREST");
    volatile float minimumNormal = floating(0x00800000), half = .5f;
    volatile float subnormalOutput = minimumNormal * half;
    volatile float minimumSubnormal = floating(1), two = 2;
    volatile float subnormalInput = minimumSubnormal * two;
    if (bits(subnormalOutput) != 0x00400000 || bits(subnormalInput) != 2)
      throw std::runtime_error(
          "requires gradual underflow with FTZ/DAZ disabled");
    if (argc != 2)
      throw std::runtime_error("vector path required");
    std::ifstream input(argv[1]);
    if (!input)
      throw std::runtime_error("cannot read vectors");
    std::map<char, unsigned> counts;
    char op;
    unsigned id;
    std::string before, after, a, b, c, returned;
    while (input >> op >> id >> before >> a >> b >> c >> returned >> after) {
      BilinearInterpolator interpolation;
      auto initial = unhex(before);
      std::memcpy(&interpolation.recoveredState(), initial.data(), 36);
      auto x = static_cast<std::uint32_t>(std::stoul(a, nullptr, 16));
      auto y = static_cast<std::uint32_t>(std::stoul(b, nullptr, 16));
      auto z = static_cast<std::uint32_t>(std::stoul(c, nullptr, 16));
      auto expected =
          static_cast<std::uint32_t>(std::stoul(returned, nullptr, 16));
      std::uint32_t result = 0;
      switch (op) {
      case 'N':
        result = bits(interpolation.normalizedToRange(floating(x)));
        break;
      case 'R':
        result = bits(interpolation.rangeToNormalized(floating(x)));
        break;
      case 'M':
        interpolation.setMidPoint(floating(x), floating(y));
        break;
      case 'S':
        interpolation.setRange(floating(x), floating(y), floating(z));
        break;
      case 'G': {
        ShelbyGEQController controller;
        result = bits(controller.denormalizeValue(floating(x)));
        break;
      }
      case 'E':
        result = static_cast<std::uint32_t>(
            EQController::biquadFromBandType(static_cast<EqType>(x)));
        break;
      default:
        throw std::runtime_error("unknown operation");
      }
      if (result != expected) {
        std::cerr << op << id << " result expected=" << std::hex << expected
                  << " actual=" << result << " input=" << x << '\n';
        throw std::runtime_error("original ARM result mismatch");
      }
      auto changed = unhex(after);
      if (std::memcmp(&interpolation.recoveredState(), changed.data(), 36)) {
        const auto *bytes = reinterpret_cast<const unsigned char *>(
            &interpolation.recoveredState());
        for (unsigned offset = 0; offset < 36; offset += 4)
          if (std::memcmp(bytes + offset, changed.data() + offset, 4)) {
            std::uint32_t actual, wanted;
            std::memcpy(&actual, bytes + offset, 4);
            std::memcpy(&wanted, changed.data() + offset, 4);
            std::cerr << op << id << " state byte=" << offset
                      << " expected=" << std::hex << wanted
                      << " actual=" << actual << '\n';
            break;
          }
        throw std::runtime_error("original ARM state mismatch");
      }
      ++counts[op];
    }
    if ((counts.size() != 4 && counts.size() != 6) || !counts.count('M') ||
        !counts.count('S') || !counts.count('N') || !counts.count('R'))
      throw std::runtime_error("missing operation coverage");
    std::cout << "PASS:";
    for (auto [op, count] : counts)
      std::cout << ' ' << op << '=' << count;
    std::cout << " original ARM differential cases\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
