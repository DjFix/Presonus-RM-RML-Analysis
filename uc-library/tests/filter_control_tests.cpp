#include "presonus/mixer_dsp/FilterControllers.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

float value(std::uint32_t bits) {
  float result;
  std::memcpy(&result, &bits, 4);
  return result;
}
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::runtime_error("fixture path required");
    std::ifstream input(argv[1]);
    if (!input)
      throw std::runtime_error("fixture unavailable");
    std::array<unsigned, 256> counts{};
    char op;
    int index;
    unsigned dirty, active, pending, wantDirty, wantActive, wantPending;
    std::string raw, prior, returned, changed;
    while (input >> op >> index >> raw >> prior >> dirty >> active >> pending >>
           returned >> changed >> wantDirty >> wantActive >> wantPending) {
      auto parse = [](const std::string &s) {
        return static_cast<std::uint32_t>(std::stoul(s, nullptr, 16));
      };
      Presonus::Dsp::FilterControllerState state{
          parse(prior), static_cast<std::uint8_t>(dirty),
          static_cast<std::uint8_t>(active),
          static_cast<std::uint8_t>(pending)};
      Presonus::Dsp::HiPassController high(state);
      Presonus::Dsp::LoPassController low(state);
      std::uint32_t result = 0;
      switch (op) {
      case 'H':
        high.setValue(index, value(parse(raw)));
        break;
      case 'L':
        low.setValue(index, value(parse(raw)));
        break;
      case 'h':
        result = bits(high.getValue(index));
        break;
      case 'l':
        result = bits(low.getValue(index));
        break;
      default:
        throw std::runtime_error("unknown operation");
      }
      if (result != parse(returned) || state.valueBits != parse(changed) ||
          state.dirty != wantDirty || state.active != wantActive ||
          state.pending != wantPending) {
        std::cerr << op << " index=" << index << " input=" << raw << '\n';
        throw std::runtime_error("original ARM result/state mismatch");
      }
      ++counts[static_cast<unsigned char>(op)];
    }
    if (!input.eof())
      throw std::runtime_error("malformed fixture");
    for (char operation : {'H', 'L', 'h', 'l'}) {
      if (counts[operation] != 2700)
        throw std::runtime_error("incomplete fixture coverage");
      std::cout << operation << '=' << counts[operation] << ' ';
    }
    std::cout << "original ARM cases passed\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
