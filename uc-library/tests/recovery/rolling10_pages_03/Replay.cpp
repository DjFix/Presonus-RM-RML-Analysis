#include "presonus/ModalPageComponent.hpp"
#include <iostream>
int main() {
  Presonus::ModalPageComponent first, second;
  int id;
  unsigned address;
  while (std::cin >> id >> address) {
    auto &object = address == 0x1000000 ? first : second;
    void *result = object.castTo(id);
    if (result != nullptr && result != &object)
      return 2;
    std::cout << (result == &object) << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
