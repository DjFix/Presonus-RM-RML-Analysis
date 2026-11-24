#include "presonus/surface_panel/ControlHelpers.hpp"

#include <array>
#include <cstring>
#include <iostream>

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using Presonus::Panel::ControlRegistrar;
  ControlRegistrar registrar;
  ControlRegistrar::Delegate receiver;
  for (unsigned tag : {0, 127, 255}) {
    std::array<unsigned char, 4> payload{0xa5, 0x1f, 0x98, 0x42};
    const auto previousPayload = payload;
    const auto previousReceiver = snapshot(receiver);
    const auto previousRegistrar = snapshot(registrar);
    const bool hasPayload = tag != 0;
    receiver.controlChanged(registrar, static_cast<unsigned char>(tag),
                            hasPayload ? payload.data() : nullptr);
    std::cout << "case " << tag << ' ' << hasPayload << ' '
              << (previousReceiver == snapshot(receiver)) << ' '
              << (previousRegistrar == snapshot(registrar)) << ' '
              << (previousPayload == payload) << '\n';
  }
}
