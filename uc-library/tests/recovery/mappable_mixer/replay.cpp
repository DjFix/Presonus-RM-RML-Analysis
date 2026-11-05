#include "presonus/MappableMixer.hpp"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  Presonus::MappableMixer mixer;
  std::string task, method;
  int index;
  std::uintptr_t expected;
  unsigned count = 0;
  while (input >> task >> method >> index >> expected) {
    std::uintptr_t actual;
    if (method == "geq")
      actual = reinterpret_cast<std::uintptr_t>(mixer.getSelectedGeq());
    else if (method == "count")
      actual = static_cast<std::uintptr_t>(mixer.countAllChannels());
    else if (method == "indexed")
      actual = reinterpret_cast<std::uintptr_t>(mixer.getChannelIndexed(index));
    else
      return 3;
    if (actual != expected)
      return 4;
    ++count;
  }
  if (!input.eof() || count == 0)
    return 5;
  std::cout << count << " native observations replayed\n";
}
