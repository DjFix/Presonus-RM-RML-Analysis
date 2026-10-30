#include "presonus/utilities/string_utils.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
int main() {
  unsigned operation;
  std::string hex;
  while (std::cin >> operation >> hex) {
    if (hex.size() != 512 || operation > 1)
      return 2;
    Core::CStringBuffer<256> buffer;
    for (std::size_t index = 0; index < 256; ++index)
      buffer.getBuffer()[index] =
          static_cast<char>(std::stoul(hex.substr(index * 2, 2), nullptr, 16));
    if (!std::memchr(buffer.getBuffer(), 0, 256))
      return 3;
    if (operation == 0)
      presonus::utilities::removeWhitespace(buffer);
    else
      presonus::utilities::makeProperMixedCase(buffer);
    for (unsigned char value : std::string(buffer.getBuffer(), 256))
      std::cout << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<unsigned>(value);
    std::cout << '\n';
  }
}
