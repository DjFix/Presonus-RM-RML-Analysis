#include "presonus/surface/DisplayManager.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cstring>
#include <iostream>

namespace {
template <class T> auto snapshot(const T &value) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &value, bytes.size());
  return bytes;
}
} // namespace
int main() {
  using namespace Presonus;
  using namespace Presonus::Panel;
  ControlRegistrar registrar;
  ControlRegistrar::Delegate defaults;

  auto callback = &ControlRegistrar::Delegate::screenTouched;
  const int inputs[][2] = {{0, 0}, {-1, -2147483647 - 1}, {1, 17}};
  for (auto &input : inputs) {
    int group = input[0], index = input[1];
    const auto before = snapshot(registrar);
    const auto receiver = snapshot(defaults);
    (defaults.*callback)(registrar, TouchInputEvent{group, index, 42, 93});
    if (before != snapshot(registrar) || receiver != snapshot(defaults))
      return 5;
    std::cout << "no-effect\n";
  }
}
