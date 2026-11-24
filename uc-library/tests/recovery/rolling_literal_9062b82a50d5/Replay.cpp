#include "presonus/panel/PanelRegistrar.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <type_traits>

namespace {
template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}
} // namespace

int main() {
  using Presonus::Panel::PanelRegistrar;
  using presonus::panel_binding::PanelRegistrarPortState;
  static_assert(std::is_same_v<decltype(&PanelRegistrar::getLcdPortName),
                               const char *(PanelRegistrar::*)()>);
  const char *previous = nullptr;
  int number;
  while (std::cin >> number) {
    PanelRegistrarPortState state;
    state.descriptionNumber = number;
    state.secondaryEnabled = number != 0;
    PanelRegistrar receiver(state);
    const auto receiverBefore = snapshot(receiver);
    const auto stateBefore = snapshot(state);
    const char *portName = receiver.getLcdPortName();
    if (!portName)
      return 2;
    const auto samePointer = portName == receiver.getLcdPortName() &&
                             (!previous || previous == portName);
    const auto unchanged =
        receiverBefore == snapshot(receiver) && stateBefore == snapshot(state);
    std::cout << portName << ' ' << samePointer << ' ' << unchanged << '\n';
    previous = portName;
  }
  return std::cin.eof() ? 0 : 1;
}
