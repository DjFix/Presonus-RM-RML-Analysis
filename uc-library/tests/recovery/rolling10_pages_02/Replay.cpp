#include "presonus/MappablePageComponent.hpp"
#include <cstring>
#include <iostream>
int main() {
  Presonus::MappablePageComponent first("alpha"), second("beta");
  if (std::strcmp(first.getPageName(), "alpha") ||
      std::strcmp(second.getPageName(), "beta"))
    return 4;
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
