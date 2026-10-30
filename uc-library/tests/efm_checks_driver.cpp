#include "presonus/embedded_efm/efm_packet_checks.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main() {
  char mode;
  std::size_t capacity;
  std::string hex;
  while (std::cin >> mode >> capacity >> hex) {
    std::vector<std::uint8_t> data;
    for (std::size_t i = 0; i < hex.size(); i += 2)
      data.push_back(
          static_cast<std::uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    if (capacity > data.size())
      return 2;
    unsigned value = 0x12345678;
    bool accepted = false;
    if (mode == 'a')
      accepted = presonus::analysis::efm_fader_app::appendPacketChecks(
          data.data(), capacity);
    else if (mode == 'v')
      accepted = presonus::analysis::efm_fader_app::validatePacketChecks(
          data.data(), capacity, value);
    else
      return 3;
    std::cout << accepted << ' ' << value << ' ';
    for (auto byte : data)
      std::cout << std::hex << std::setw(2) << std::setfill('0')
                << unsigned(byte);
    std::cout << std::dec << '\n';
  }
}
