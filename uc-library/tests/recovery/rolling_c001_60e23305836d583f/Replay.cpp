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
  ControlRegistrar::Delegate receiver;
  int value1, value2;
  while (std::cin >> value1 >> value2) {
    const auto beforeReceiver = snapshot(receiver);
    const auto beforeRegistrar = snapshot(registrar);
    receiver.lineSenseChanged(registrar, value1, value2);
    std::cout << (beforeReceiver == snapshot(receiver)) << ' '
              << (beforeRegistrar == snapshot(registrar)) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
