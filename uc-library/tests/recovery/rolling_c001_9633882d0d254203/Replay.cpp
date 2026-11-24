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
  ControlRegistrar receiver;
  int value0, value1;
  while (std::cin >> value0 >> value1) {
    const auto beforeReceiver = snapshot(receiver);
    receiver.handleKeyValue(static_cast<unsigned char>(value0),
                            static_cast<unsigned short>(value1));
    std::cout << (beforeReceiver == snapshot(receiver)) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
