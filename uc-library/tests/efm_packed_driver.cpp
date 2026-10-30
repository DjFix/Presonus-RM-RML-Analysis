#include "presonus/embedded_efm/efm_packed_parameters.hpp"
#include <array>
#include <iostream>

int main() {
  std::array<std::uint8_t, 4> header;
  std::array<std::uint8_t, 4096> ram;
  while (
      std::cin.read(reinterpret_cast<char *>(header.data()), header.size())) {
    const std::uint32_t capacity =
        std::uint32_t(header[0]) | (std::uint32_t(header[1]) << 8) |
        (std::uint32_t(header[2]) << 16) | (std::uint32_t(header[3]) << 24);
    if (capacity > ram.size() ||
        !std::cin.read(reinterpret_cast<char *>(ram.data()), ram.size()))
      return 2;
    const bool accepted = presonus::analysis::efm_fader_packed_parameters::
        applyPackedParameterPacket(ram.data(), capacity);
    std::cout.put(accepted ? 1 : 0);
    std::cout.write(reinterpret_cast<const char *>(ram.data()), ram.size());
  }
  return std::cin.gcount() == 0 ? 0 : 3;
}
