#include "presonus/embedded_efm/efm_packet_checks.hpp"
#include "presonus/embedded_efm/efm_version_packet.hpp"

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main() {
  unsigned board;
  std::string hex;
  while (std::cin >> board >> hex) {
    if (board > 15 || hex.size() % 2)
      return 2;
    std::vector<std::uint8_t> packet;
    for (std::size_t i = 0; i < hex.size(); i += 2)
      packet.push_back(
          static_cast<std::uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    unsigned validation = 99;
    using namespace presonus::analysis::efm_fader_app;
    if (!validatePacketChecks(packet.data(), packet.size(), validation) ||
        validation ||
        !applyVersionPacket(packet.data(), packet.size(), board) ||
        !appendPacketChecks(packet.data(), packet.size()))
      return 3;
    std::ostringstream result;
    for (auto byte : packet)
      result << std::hex << std::setfill('0') << std::setw(2) << unsigned(byte);
    std::cout << validation << ' ' << result.str() << '\n';
  }
}
