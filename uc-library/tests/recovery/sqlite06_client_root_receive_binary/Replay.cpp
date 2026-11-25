#include "presonus/uc/ClientRootComponent.hpp"
#include "presonus/uc/data_codecs.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <string_view>

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes{};
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using namespace Presonus::UC;
  for (const char *name : {"", "root"}) {
    ClientRootComponent root(name);
    BinaryEvent input{};
    input.word24 = 123;
    const auto rootBytes = snapshot(root);
    const auto inputBytes = snapshot(input);
    root.receiveEvent(input);
    if (rootBytes != snapshot(root) || inputBytes != snapshot(input) ||
        root.getRoot() != &root || std::string_view(root.getName()) != name)
      return 1;
    std::cout << "unchanged\n";
  }
}
