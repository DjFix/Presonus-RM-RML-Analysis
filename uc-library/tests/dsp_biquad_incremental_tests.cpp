#include "presonus/dsp/biquad_calc.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>
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
float fromBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof value);
  return value;
}
template <class T>
bool compare(const std::string &method, std::uint32_t mode, std::uint32_t f,
             std::uint32_t q, std::uint32_t g, const std::string &before,
             const std::string &expected, unsigned id,
             std::ostream &differences) {
  using State = presonus::dsp::BiquadState<T>;
  auto seed = decode(before), target = decode(expected);
  if (seed.size() < sizeof(State) || seed.size() != target.size())
    throw std::runtime_error("bad extent");
  State state;
  std::memcpy(&state, seed.data(), sizeof state);
  DSP::BiquadCalc<T, false> object(presonus::dsp::BiquadSeedTag{}, state);
  if (method == "setParams")
    object.setParams(static_cast<std::int32_t>(mode), fromBits(f), fromBits(q),
                     fromBits(g));
  else if constexpr (std::is_same_v<T, double>) {
    if (method == "setQ")
      object.setQ(fromBits(f));
    else if (method == "setGain")
      object.setGain(fromBits(f));
    else if (method == "setFreq")
      object.setFreq(fromBits(f));
    else
      throw std::runtime_error("unsupported method");
  } else
    throw std::runtime_error("unsupported float method");
  std::memcpy(seed.data(), &object.portableState(), sizeof state);
  bool same = true;
  for (std::size_t i = 0; i < seed.size(); ++i)
    if (seed[i] != target[i]) {
      differences << id << ' ' << i << ' ' << unsigned(target[i]) << ' '
                  << unsigned(seed[i]) << '\n';
      same = false;
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
  std::uint32_t mode, f, q, g;
  unsigned cases = 0, failed = 0;
  while (in >> role >> method >> mode >> f >> q >> g >> before >> expected) {
    ++cases;
    failed +=
        !(role == "server" ? compare<double>(method, mode, f, q, g, before,
                                             expected, cases, differences)
                           : compare<float>(method, mode, f, q, g, before,
                                            expected, cases, differences));
  }
  std::cout << "{\"cases\":" << cases << ",\"mismatches\":" << failed
            << ",\"exact\":" << (failed ? "false" : "true") << "}\n";
  return failed ? 3 : 0;
}
