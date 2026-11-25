#include "presonus/uc/ClientComponent.hpp"
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  Presonus::UC::ClientComponent object("cast-receiver");
  Core::Portable::TypedObject &base = object;
  void *result = base.castTo(std::stoi(argv[1]));
  if (result != &object && result != nullptr)
    return 2;
  std::cout << int(result == &object) << '\n';
}
