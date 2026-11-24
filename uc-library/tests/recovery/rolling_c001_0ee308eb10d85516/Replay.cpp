#include "presonus/panel/PanelRegistrar.hpp"

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
  presonus::panel_binding::PanelRegistrarPortState state;
  PanelRegistrar receiver(state);
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream args(line);
    const auto a = snapshot(receiver);
    receiver.bootComplete();
    std::cout << (a == snapshot(receiver)) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
