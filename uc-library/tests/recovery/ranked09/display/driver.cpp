#include "presonus/surface/DisplayManager.hpp"
#include <cstdint>
#include <iostream>
int main() {
  std::uint64_t input;
  while (std::cin >> input) {
    auto *p = reinterpret_cast<Presonus::DisplayManager *>(
        static_cast<std::uintptr_t>(input));
    presonus::surface_display_port::DisplayManagerAccess::bindInstance(p);
    std::cout << reinterpret_cast<std::uintptr_t>(
                     Presonus::DisplayManager::getInstance())
              << "\n";
  }
}
