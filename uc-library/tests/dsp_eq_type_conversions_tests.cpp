#include "presonus/mixer_dsp/Dsp.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <type_traits>

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  static_assert(std::is_polymorphic_v<Presonus::Dsp::EQController>);
  static_assert(std::is_base_of_v<Presonus::Dsp::EQController,
                                  Presonus::Dsp::EQ8Controller>);
  const Presonus::Dsp::EQController base(presonus::dsp::EQTypePortTag{});
  const Presonus::Dsp::EQ8Controller eight(presonus::dsp::EQTypePortTag{});
  unsigned char baseBefore[sizeof base], eightBefore[sizeof eight];
  std::memcpy(baseBefore, &base, sizeof base);
  std::memcpy(eightBefore, &eight, sizeof eight);
  std::ifstream input(argv[1]);
  std::ofstream differences(argv[2]);
  std::string kind;
  std::uint32_t word, expected;
  unsigned cases = 0, failed = 0;
  while (input >> kind >> word >> expected) {
    std::int32_t signedWord;
    std::memcpy(&signedWord, &word, sizeof word);
    const auto type = static_cast<DSP::BiquadType>(signedWord);
    const Presonus::Dsp::EQController &object =
        kind == "base" || kind == "base_inverse" ? base : eight;
    const bool inverse = kind == "base_inverse" || kind == "eight_inverse";
    const auto actual =
        inverse ? object.getBiquadType(signedWord) : object.getEQType(type);
    ++cases;
    if (actual != static_cast<int>(expected)) {
      ++failed;
      differences << cases << ' ' << word << ' ' << expected << ' ' << actual
                  << '\n';
    }
  }
  if (std::memcmp(baseBefore, &base, sizeof base) ||
      std::memcmp(eightBefore, &eight, sizeof eight))
    return 4;
  std::cout << "{\"cases\":" << cases << ",\"mismatches\":" << failed
            << ",\"exact\":" << (failed ? "false" : "true") << "}\n";
  return cases && failed == 0 ? 0 : 3;
}
