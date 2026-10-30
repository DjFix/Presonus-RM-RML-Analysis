#include "efm_control_dispatch.hpp"
#include <array>
#include <iostream>
#include <vector>

namespace {
using namespace presonus::analysis::efm_fader_control_dispatch;
class Capture final : public ControlBoundary {
public:
  std::vector<std::array<std::uint32_t, 3>> calls;
  void call(ControlEntry entry, std::uint32_t context,
            std::uint32_t argument) override {
    calls.push_back({static_cast<std::uint32_t>(entry), context, argument});
  }
};
void word(std::uint32_t value) {
  for (unsigned i = 0; i < 4; ++i)
    std::cout.put(static_cast<char>(value >> (i * 8)));
}
} // namespace
int main() {
  std::array<std::uint8_t, 5> header;
  std::array<std::uint8_t, 4096> ram;
  while (
      std::cin.read(reinterpret_cast<char *>(header.data()), header.size())) {
    const auto capacity =
        std::uint32_t(header[1]) | (std::uint32_t(header[2]) << 8) |
        (std::uint32_t(header[3]) << 16) | (std::uint32_t(header[4]) << 24);
    if (header[0] > 1 || capacity > ram.size() ||
        !std::cin.read(reinterpret_cast<char *>(ram.data()), ram.size()))
      return 2;
    Capture capture;
    const bool accepted =
        header[0] ? initialiseIndexedState(ram.data(), capacity)
                  : dispatchControlPacket(ram.data(), capacity, capture);
    if (capture.calls.size() > 2)
      return 3;
    std::cout.put(accepted ? 1 : 0);
    std::cout.write(reinterpret_cast<const char *>(ram.data()), ram.size());
    std::cout.put(static_cast<char>(capture.calls.size()));
    for (std::size_t i = 0; i < 2; ++i)
      for (unsigned j = 0; j < 3; ++j)
        word(i < capture.calls.size() ? capture.calls[i][j] : 0);
  }
  return std::cin.gcount() == 0 ? 0 : 4;
}
