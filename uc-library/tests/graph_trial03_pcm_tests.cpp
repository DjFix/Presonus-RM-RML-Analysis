#include "presonus/pcm4104/Pcm4104Spi.hpp"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>

int main(int argc, char **argv) {
  static_assert(sizeof(int) == 4);
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  if (!input)
    return 3;
  Presonus::PCM4104::Pcm4104Spi object;
  std::int64_t channel;
  std::uint64_t expected;
  unsigned count = 0;
  while (input >> channel >> expected) {
    if (channel < std::numeric_limits<int>::min() ||
        channel > std::numeric_limits<int>::max() || expected > UINT32_MAX)
      return 4;
    if (object.lookupChannelAttenuationRegister(static_cast<int>(channel)) !=
        expected)
      return 5;
    ++count;
  }
  if (!input.eof() || !count)
    return 6;
  std::cout << count
            << " native ARM fixture cases passed; signed int32 inputs, "
            << "unsigned 32-bit outputs\n";
}
