#include "presonus/mixer/MicLineComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
int main() {
  Presonus::Mixer::MicLineComponent component;
  std::uint32_t input;
  int alias;
  while (std::cin >> input >> alias) {
    float gain, outputs[2];
    std::uint32_t initial[] = {0xdeadbeefU, 0xabadcafeU};
    std::memcpy(&gain, &input, 4);
    std::memcpy(outputs, initial, 8);
    int status = component.calculateDigitalMicPreampGainDivision(
        outputs, outputs + (alias ? 0 : 1), gain);
    std::uint32_t result[2];
    std::memcpy(result, outputs, 8);
    std::cout << static_cast<std::uint32_t>(status) << ' ' << result[0] << ' '
              << result[1] << '\n';
  }
}
