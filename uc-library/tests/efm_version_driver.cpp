#include "presonus/embedded_efm/efm_version_packet.hpp"
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
int main() {
  unsigned board;
  std::size_t capacity;
  std::string hex;
  while (std::cin >> board >> capacity >> hex) {
    std::vector<std::uint8_t> data;
    for (std::size_t i = 0; i < hex.size(); i += 2)
      data.push_back(
          static_cast<std::uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    if (capacity > data.size() || board > 255)
      return 2;
    std::cout << presonus::analysis::efm_fader_app::applyVersionPacket(
                     data.data(), capacity, static_cast<std::uint8_t>(board))
              << ' ';
    for (auto byte : data)
      std::cout << std::hex << std::setw(2) << std::setfill('0')
                << unsigned(byte);
    std::cout << std::dec << '\n';
  }
}
