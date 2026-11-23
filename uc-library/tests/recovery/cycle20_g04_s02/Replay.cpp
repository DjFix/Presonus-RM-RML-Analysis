#include "presonus/mixer/MixerComponentBase.hpp"
#include <array>
#include <cstdint>
#include <iostream>

struct Payload : Core::Property {
  Payload(int type, int byteSize, std::uint32_t sentinel)
      : Core::Property(type, byteSize), marker{sentinel, ~sentinel} {}
  std::array<std::uint32_t, 2> marker;
};

int main() {
  Presonus::Mixer::MixerComponentBase mixer;
  int type = 0;
  int byteSize = 0;
  std::uint32_t sentinel = 0;
  while (std::cin >> type >> byteSize >> sentinel) {
    Payload property(type, byteSize, sentinel);
    mixer.getProperty(property);
    std::cout << property.type << ' ' << property.size << ' '
              << property.marker[0] << ' ' << property.marker[1] << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
