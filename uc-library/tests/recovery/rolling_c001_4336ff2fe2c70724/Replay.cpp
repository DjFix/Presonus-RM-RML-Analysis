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

int main() {
  using namespace Presonus::Panel;
  Presonus::Surface::SurfaceRootComponent receiver;
  ControlRegistrar registrar;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream args(line);
    const auto a = snapshot(receiver);
    const auto b = snapshot(registrar);
    int x, y, z, w;
    if (!(args >> x >> y >> z >> w))
      return 2;
    receiver.screenTouched(registrar, x, y, z, w);
    std::cout << (a == snapshot(receiver)) << ' ' << (b == snapshot(registrar))
              << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
