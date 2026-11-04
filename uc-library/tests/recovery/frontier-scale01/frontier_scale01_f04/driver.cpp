#include "presonus/uc/NetworkItem.hpp"
#include <cstdint>
#include <iostream>

int main() {
  std::uintptr_t word;
  while (std::cin >> word) {
    // Integer tokens represent opaque borrowed addresses and are never
    // dereferenced.
    const Presonus::UC::NetworkItem item(reinterpret_cast<void *>(word));
    const auto first = reinterpret_cast<std::uintptr_t>(item.getComponent());
    const auto second = reinterpret_cast<std::uintptr_t>(item.getComponent());
    if (first != second)
      return 1;
    std::cout << first << '\n';
  }
}
