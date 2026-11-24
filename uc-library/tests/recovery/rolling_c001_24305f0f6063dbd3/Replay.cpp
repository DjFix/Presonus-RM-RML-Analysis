#include "presonus/surface_panel/ControlHelpers.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {
template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}
} // namespace

int main() {
  using namespace Presonus::Panel;
  ControlRegistrar registrar;
  Presonus::Surface::SurfaceRootComponent receiver;
  std::array<unsigned char, 4> pointed{0xa5, 0x1f, 0x98, 0x42};
  int value1, value2;
  while (std::cin >> value1 >> value2) {
    const auto beforeReceiver = snapshot(receiver);
    const auto beforeRegistrar = snapshot(registrar);
    const auto beforePointed = snapshot(pointed);
    receiver.controlChanged(registrar, static_cast<unsigned char>(value1),
                            value2 ? pointed.data() : nullptr);
    std::cout << (beforeReceiver == snapshot(receiver)) << ' '
              << (beforeRegistrar == snapshot(registrar)) << ' '
              << (beforePointed == snapshot(pointed)) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
