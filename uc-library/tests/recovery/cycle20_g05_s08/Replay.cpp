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
  PotControl control(2);
  auto callback = &ControlRegistrar::Delegate::potChanged;
  const int inputs[][2] = {{0, 0}, {-1, -2147483647 - 1}, {1, 17}};
  for (auto &input : inputs) {
    int group = input[0], index = input[1];
    const auto before = snapshot(registrar);
    const auto receiver = snapshot(defaults);
    const auto controlBefore = snapshot(control);
    (defaults.*callback)(registrar, group, index, &control);
    if (before != snapshot(registrar) || receiver != snapshot(defaults) ||
        controlBefore != snapshot(control))
      return 5;
    std::cout << "no-effect\n";
  }
}
