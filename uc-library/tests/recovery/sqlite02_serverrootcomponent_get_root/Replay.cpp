#include "presonus/uc/ServerRootComponent.hpp"

#include <iostream>

int main() {
  Presonus::UC::ServerRootComponent root("local root");
  int sample;
  while (std::cin >> sample) {
    std::cout << (root.getRoot() == &root) << '\n';
  }
}
