#include "presonus/embedded_efm/efm_parameter_fields.hpp"
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
namespace {
std::vector<std::uint8_t> decode(const std::string &hex) {
  std::vector<std::uint8_t> result;
  for (std::size_t i = 0; i < hex.size(); i += 2)
    result.push_back(
        static_cast<std::uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  return result;
}
void print(const std::vector<std::uint8_t> &bytes) {
  for (auto byte : bytes)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << unsigned(byte);
  std::cout << std::dec;
}
} // namespace
int main() {
  unsigned kind, board, first, last;
  std::uint32_t stateStride, packetStride;
  std::size_t packetCapacity, stateCapacity;
  std::string packetHex, stateHex;
  while (std::cin >> kind >> board >> first >> last >> stateStride >>
         packetStride >> packetCapacity >> stateCapacity >> packetHex >>
         stateHex) {
    auto packet = decode(packetHex);
    auto state = decode(stateHex);
    if (kind > 4 || board > 255 || first > 255 || last > 255 ||
        packetCapacity > packet.size() || stateCapacity > state.size())
      return 2;
    using namespace presonus::analysis::efm_fader_parameters;
    const bool accepted =
        kind == 4 ? applyParameterPacket(packet.data(), packetCapacity,
                                         state.data(), stateCapacity,
                                         static_cast<std::uint8_t>(board))
                  : transferStrided(static_cast<Transfer>(kind), packet.data(),
                                    packetCapacity, state.data(), stateCapacity,
                                    stateStride, packetStride,
                                    static_cast<std::uint8_t>(first),
                                    static_cast<std::uint8_t>(last));
    std::cout << accepted << ' ';
    print(packet);
    std::cout << ' ';
    print(state);
    std::cout << '\n';
  }
}
