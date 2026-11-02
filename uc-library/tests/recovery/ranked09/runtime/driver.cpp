#include "presonus/dsp/RuntimeGlobals.hpp"
#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>
#include <tuple>
#include <vector>
struct Memory {
  std::map<std::uint32_t, std::uint32_t> words;
  std::vector<std::tuple<char, std::uint32_t, std::uint32_t>> trace;
};
std::uint32_t read(void *context, std::uint32_t address) {
  auto &m = *static_cast<Memory *>(context);
  const auto value = m.words.at(address);
  m.trace.emplace_back('R', address, value);
  return value;
}
void write(void *context, std::uint32_t address, std::uint32_t value) {
  auto &m = *static_cast<Memory *>(context);
  m.words.at(address) = value;
  m.trace.emplace_back('W', address, value);
}
int main() {
  unsigned target;
  std::uint32_t link, field, seed;
  while (std::cin >> target >> link >> field >> seed) {
    Memory m;
    m.words = {{0x494054U, 0x200000U}, {0x20001cU, field},
               {0x49db64U, link},      {link + 0x3decU, field},
               {link + 0x3df0U, seed}, {link + 0x3df4U, field}};
    presonus::dsp::bindRuntimeMemory({&m, read, write});
    std::uint32_t result = 0;
    switch (target) {
    case 0:
      result = Presonus::Dsp::getAudioHAL();
      break;
    case 1:
      result = getSharedLink();
      break;
    case 2:
      result = getDSPState();
      break;
    case 3:
      result = isLinkReady();
      break;
    case 4:
      shutdownDSP();
      break;
    default:
      return 2;
    }
    std::cout << result << ' ' << m.words.at(link + 0x3df0U) << ' '
              << m.trace.size();
    for (auto [kind, address, value] : m.trace)
      std::cout << ' ' << kind << ' ' << address << ' ' << value;
    std::cout << '\n';
  }
}
