#include "presonus/uc/ServerRootComponent.hpp"

#include <iostream>

int main() {
  Presonus::UC::ServerRootComponent root("local root");
  Core::Portable::TypedObject &receiver = root;
  if (Core::Portable::core_cast<Presonus::UC::ServerRootComponent>(&receiver) !=
      &root)
    return 1;
  int typeId;
  while (std::cin >> typeId) {
    void *result = receiver.castTo(typeId);
    if (result && result != static_cast<void *>(&root))
      return 1;
    std::cout << (result != nullptr) << '\n';
  }
}
