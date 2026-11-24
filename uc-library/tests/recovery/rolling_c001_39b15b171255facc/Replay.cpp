#include "presonus/surface_panel/ControlHelpers.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

namespace {
template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}
} // namespace

// Test-only stand-in, referenced by the opaque callback.
namespace Presonus {
class WIFIManager {
public:
  int sentinel;
};
} // namespace Presonus

int main() {
  using namespace Presonus::Panel;
  Presonus::Surface::SurfaceRootComponent receiver;
  Presonus::WIFIManager manager{0x5a};
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream args(line);
    const auto a = snapshot(receiver);
    const auto b = snapshot(manager);
    receiver.networkChanged(manager);
    std::cout << (a == snapshot(receiver)) << ' ' << (b == snapshot(manager))
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
