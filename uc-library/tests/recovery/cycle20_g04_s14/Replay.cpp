#include "presonus/MixerClientComponentBase.hpp"
#include <iostream>
#include <string>

int main() {
  Presonus::MixerClientComponentBase receiver;
  std::string input;
  while (std::getline(std::cin, input)) {
    if (input == "-")
      std::cout << int(receiver.translatePresetType(nullptr)) << '\n';
    else {
      if (input.empty() || input.front() != ':')
        return 1;
      std::cout << int(receiver.translatePresetType(input.c_str() + 1)) << '\n';
    }
  }
  return std::cin.eof() ? 0 : 1;
}
