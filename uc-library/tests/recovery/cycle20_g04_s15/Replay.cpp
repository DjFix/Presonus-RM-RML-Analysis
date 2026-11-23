#include "presonus/MixerClientComponentBase.hpp"
#include <cstring>
#include <iostream>

int main() {
  Presonus::MixerClientComponentBase receiver;
  constexpr char hex[] = "0123456789abcdef";
  int type = 0;
  while (std::cin >> type) {
    Core::CStringBuffer<128> output;
    std::memset(output.getBuffer(), 0x7d, 128);
    const auto value = static_cast<Presonus::IPresetHandler::PresetType>(type);
    receiver.getPresetType(value, output);
    for (int i = 0; i != 128; ++i) {
      const auto byte = static_cast<unsigned char>(output.getBuffer()[i]);
      std::cout << hex[byte >> 4] << hex[byte & 0xF];
    }
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
