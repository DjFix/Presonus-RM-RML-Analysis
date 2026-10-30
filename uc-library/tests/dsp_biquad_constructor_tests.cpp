#include "presonus/dsp/biquad_calc.hpp"

#include <array>
#include <cstddef>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <string>

namespace {
bool decode(const std::string &text, unsigned char *out, std::size_t count) {
  if (text.size() != count * 2)
    return false;
  for (std::size_t i = 0; i < count; ++i)
    out[i] = static_cast<unsigned char>(
        std::stoul(text.substr(i * 2, 2), nullptr, 16));
  return true;
}
} // namespace

int main(int argc, char **argv) {
  using Object = DSP::BiquadCalc<double, false>;
  using State = presonus::dsp::BiquadState<double>;
  static_assert(sizeof(Object) == 0x128);
  static_assert(offsetof(State, rate) == 0x58);
  static_assert(offsetof(State, coefficients) == 0x78);
  static_assert(offsetof(State, temporary) == 0xc0);
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string before, after;
  unsigned cases = 0;
  while (input >> before >> after) {
    alignas(Object) std::array<unsigned char, 0x170> memory;
    memory.fill(0x5c);
    std::array<unsigned char, 0x130> expected;
    if (!decode(before, memory.data() + 0x20, 0x130) ||
        !decode(after, expected.data(), expected.size()))
      return 3;
    auto *object = new (memory.data() + 0x20) Object;
    if (std::memcmp(memory.data() + 0x20, expected.data(), expected.size()))
      return 4;
    for (unsigned i = 0; i < 0x20; ++i)
      if (memory[i] != 0x5c || memory[0x150 + i] != 0x5c)
        return 5;
    object->~Object();
    ++cases;
  }
  if (cases != 3)
    return 6;
  std::cout << "PASS " << cases
            << " original Biquad double C1 state fixtures\n";
}
