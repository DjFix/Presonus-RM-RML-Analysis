#include "presonus/dsp/biquad_calc.hpp"

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::vector<unsigned char> decode(const std::string &s) {
  if (s.size() % 2)
    throw std::runtime_error("odd fixture extent");
  std::vector<unsigned char> bytes;
  for (std::size_t i = 0; i < s.size(); i += 2)
    bytes.push_back(
        static_cast<unsigned char>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return bytes;
}

template <class T>
bool compare(const std::string &method, const std::string &before,
             const std::string &expected, std::uint64_t rateBits, unsigned id,
             std::ostream &differences) {
  using State = presonus::dsp::BiquadState<T>;
  auto seed = decode(before), target = decode(expected);
  if (seed.size() < sizeof(State) || seed.size() != target.size())
    throw std::runtime_error("bad fixture extent");
  State state;
  std::memcpy(&state, seed.data(), sizeof state);
  DSP::BiquadCalc<T, false> object(presonus::dsp::BiquadSeedTag{}, state);
  if (method == "flush")
    object.flush();
  else if (method == "setup") {
    double rate;
    std::memcpy(&rate, &rateBits, sizeof rate);
    object.setup(-123, rate); // Original ignores this encoded int argument.
  } else
    throw std::runtime_error("unsupported method");
  std::memcpy(seed.data(), &object.portableState(), sizeof state);
  bool same = true;
  for (std::size_t i = 0; i < seed.size(); ++i) {
    if (seed[i] != target[i]) {
      differences << id << ' ' << i << ' ' << unsigned(target[i]) << ' '
                  << unsigned(seed[i]) << '\n';
      same = false;
    }
  }
  return same;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  std::ifstream in(argv[1]);
  std::ofstream differences(argv[2]);
  std::string role, method, before, expected;
  std::uint64_t rateBits;
  unsigned cases = 0, failed = 0;
  while (in >> role >> method >> rateBits >> before >> expected) {
    ++cases;
    failed +=
        !(role == "server" ? compare<double>(method, before, expected, rateBits,
                                             cases, differences)
                           : compare<float>(method, before, expected, rateBits,
                                            cases, differences));
  }
  std::cout << "{\"cases\":" << cases << ",\"mismatches\":" << failed
            << ",\"exact\":" << (failed ? "false" : "true") << "}\n";
  return failed ? 3 : 0;
}
