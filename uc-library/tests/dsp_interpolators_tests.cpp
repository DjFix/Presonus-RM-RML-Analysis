#include "presonus/mixer_dsp/Interpolators.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

namespace {
float floating(std::uint32_t word) {
  float result;
  std::memcpy(&result, &word, 4);
  return result;
}
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
template <class Type>
bool check(char operation, const presonus::dsp::InterpolationState &seed,
           const std::uint32_t (&args)[3], std::uint32_t expectedReturn,
           const presonus::dsp::InterpolationState &expected, unsigned fields,
           unsigned id, std::ostream &differences) {
  Type object(presonus::dsp::InterpolationPortTag{}, seed);
  Core::Interpolator &interface = object;
  std::uint32_t result = 0;
  if (operation == 'S')
    interface.setRange(floating(args[0]), floating(args[1]), floating(args[2]));
  else if (operation == 'N')
    result = bits(interface.normalizedToRange(floating(args[0])));
  else
    result = bits(interface.rangeToNormalized(floating(args[0])));
  bool same = true;
  if (operation != 'S' && result != expectedReturn) {
    differences << id << " return " << expectedReturn << ' ' << result << '\n';
    same = false;
  }
  const auto after = object.portableState();
  for (unsigned field = 0; field < fields; ++field)
    if (bits(after[field]) != bits(expected[field])) {
      differences << id << " field " << field << ' ' << bits(expected[field])
                  << ' ' << bits(after[field]) << '\n';
      same = false;
    }
  return same;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  std::ifstream input(argv[1]);
  std::ofstream differences(argv[2]);
  std::string role, kind;
  char operation;
  unsigned cases = 0, failed = 0;
  std::uint32_t args[3], word, expectedReturn;
  while (input >> role >> kind >> operation >> args[0] >> args[1] >> args[2]) {
    const unsigned fields = kind == "ratio" ? 6 : kind == "exp" ? 8 : 7;
    presonus::dsp::InterpolationState seed{}, expected{};
    for (unsigned i = 0; i < fields; ++i) {
      input >> word;
      seed[i] = floating(word);
    }
    input >> expectedReturn;
    for (unsigned i = 0; i < fields; ++i) {
      input >> word;
      expected[i] = floating(word);
    }
    ++cases;
    bool same;
    if (kind == "ratio")
      same = check<Presonus::Dsp::RatioInterpolator>(
          operation, seed, args, expectedReturn, expected, fields, cases,
          differences);
    else if (kind == "exp")
      same = check<Presonus::Dsp::ExpInterpolator>(operation, seed, args,
                                                   expectedReturn, expected,
                                                   fields, cases, differences);
    else
      same = check<Presonus::Dsp::SkewInterpolator>(operation, seed, args,
                                                    expectedReturn, expected,
                                                    fields, cases, differences);
    failed += !same;
  }
  std::cout << "{\"cases\":" << cases << ",\"mismatches\":" << failed
            << ",\"exact\":" << (failed ? "false" : "true") << "}\n";
  return cases && failed == 0 ? 0 : 3;
}
