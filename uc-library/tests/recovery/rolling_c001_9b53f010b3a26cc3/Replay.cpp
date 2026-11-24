#include "presonus/mixer_state/MixerState.hpp"
#include <array>
#include <iostream>

int main() {
  using Handler = Presonus::IPresetHandler;
  Handler first;
  Handler second;
  const auto hook = &Handler::beginAuditioningPresets;
  int type, index, option, letter, length, receiver, hasName;
  while (std::cin >> type >> index >> option >> letter >> length >> receiver >>
         hasName) {
    if (length < 0 || length > 127 || letter < 65 || letter > 90 ||
        receiver < 0 || receiver > 1 || hasName < 0 || hasName > 1)
      return 2;
    Core::CStringBuffer<128> buffer;
    auto *bytes = buffer.getBuffer();
    for (int i = 0; i < buffer.getSize(); ++i)
      bytes[i] = static_cast<char>(letter);
    bytes[length] = '\0';
    auto *handler = receiver == 0 ? &first : &second;
    std::array<char, 7> name{'P', 'r', 'e', 's', 'e', 't', '\0'};
    (handler->*hook)(static_cast<Handler::PresetType>(type), index);
    for (int i = 0; i < buffer.getSize(); ++i)
      std::cout << static_cast<unsigned>(static_cast<unsigned char>(bytes[i]))
                << ' ';
    for (char ch : name)
      std::cout << static_cast<unsigned>(static_cast<unsigned char>(ch)) << ' ';
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
