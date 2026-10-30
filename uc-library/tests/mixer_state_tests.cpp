#include "presonus/mixer_state/MixerState.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>

std::uint32_t bits(std::int32_t value) {
  std::uint32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
std::int32_t signedWord(std::uint32_t value) {
  std::int32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
struct Override : Presonus::MixerClientComponentBase {
  std::uint32_t result = 0;
  mutable unsigned calls = 0;
  std::int32_t getNumGeqs() const override {
    ++calls;
    return signedWord(result);
  }
};
bool equal(const Presonus::PortableMixerState &a,
           const Presonus::PortableMixerState &b) {
  return a.masterWord == b.masterWord && a.slaveWord == b.slaveWord &&
         a.hasGeqConfiguration == b.hasGeqConfiguration &&
         a.geqCountWord == b.geqCountWord;
}
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::runtime_error("fixture path required");
    std::ifstream file(argv[1]);
    if (!file)
      throw std::runtime_error("fixture open failed");
    char op;
    std::uint32_t type, present, count, master, slave, overridden, expected,
        calls;
    std::map<char, unsigned> counts;
    while (file >> op >> std::hex >> type >> present >> count >> master >>
           slave >> overridden >> expected >> calls) {
      Presonus::MixerClientComponentBase base;
      Presonus::MixerClientComponent component;
      Override override;
      Presonus::PortableMixerState state{master, slave, present != 0, count};
      base.portableState() = state;
      override.portableState() = state;
      override.result = overridden;
      std::uint32_t actual = 0, actualCalls = 0;
      switch (op) {
      case 'S':
        actual = base.isStereoChannelType(
            static_cast<Presonus::ChannelType>(signedWord(type)));
        break;
      case 'A':
        actual = component.isAggregateMeteringChannelType(
            static_cast<Presonus::ChannelType>(signedWord(type)));
        break;
      case 'G':
        actual = bits(base.getNumGeqs());
        break;
      case 'M':
        actual = bits(base.getNumMixGeqs());
        break;
      case 'C':
        actual = base.getCascadeState();
        break;
      case 'O':
        actual = bits(override.getNumMixGeqs());
        actualCalls = override.calls;
        break;
      default:
        throw std::runtime_error("unknown operation");
      }
      if (actual != expected || actualCalls != calls ||
          !equal(base.portableState(), state) ||
          !equal(override.portableState(), state)) {
        std::cerr << op << " case=" << counts[op] << " expected=" << std::hex
                  << expected << " actual=" << actual
                  << " calls=" << actualCalls << '\n';
        throw std::runtime_error(
            "original ARM result/state/virtual-call mismatch");
      }
      ++counts[op];
    }
    if (!file.eof() || counts.size() != 6)
      throw std::runtime_error("incomplete fixtures");
    std::cout << "PASS:";
    for (const auto &[name, count] : counts)
      std::cout << ' ' << name << '=' << std::dec << count;
    std::cout << " exact ARM return words, unchanged state and override-call "
                 "counts\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
