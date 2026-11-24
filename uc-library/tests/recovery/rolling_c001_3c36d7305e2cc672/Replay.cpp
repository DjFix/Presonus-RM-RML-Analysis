#include "presonus/panel/encoder_control.hpp"
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
  EncoderControl pointed(37);
  int value1, value2, value3;
  while (std::cin >> value1 >> value2 >> value3) {
    const auto beforeReceiver = snapshot(receiver);
    const auto beforeRegistrar = snapshot(registrar);
    const auto beforePointed = snapshot(pointed);
    receiver.encoderChanged(registrar, value1, value2,
                            value3 ? &pointed : nullptr);
    std::cout << (beforeReceiver == snapshot(receiver)) << ' '
              << (beforeRegistrar == snapshot(registrar)) << ' '
              << (beforePointed == snapshot(pointed)) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
